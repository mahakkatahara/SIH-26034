"""Tests — Inspection CRUD endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_inspection(client, inspector_token):
    resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Test inspection"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["inspection_number"].startswith("LMIS-")
    assert data["status"] == "DRAFT"
    assert data["overall_compliance_status"] == "PENDING"
    return data["id"]


@pytest.mark.asyncio
async def test_list_inspections(client, inspector_token):
    resp = await client.get(
        "/api/v1/inspections",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_get_inspection_detail(client, inspector_token):
    # Create first
    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Detail test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    inspection_id = create_resp.json()["id"]

    # Get detail
    resp = await client.get(
        f"/api/v1/inspections/{inspection_id}",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == inspection_id
    assert "images" in data
    assert "declarations" in data
    assert "violations" in data


@pytest.mark.asyncio
async def test_viewer_cannot_create_inspection(client, db_session):
    """VIEWER role should not be allowed to create inspections."""
    from app.models.user import User
    from app.core.security import hash_password

    viewer = User(
        email="testviewer2@test.com",
        hashed_password=hash_password("TestViewer@123"),
        full_name="Viewer User",
        role="VIEWER",
    )
    db_session.add(viewer)
    await db_session.commit()

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "testviewer2@test.com", "password": "TestViewer@123"},
    )
    token = login_resp.json()["access_token"]

    resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Viewer test"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_analyze_inspection_stub(client, inspector_token):
    """The analyze endpoint should return a DEV_STUB result in stub mode."""
    from unittest.mock import patch
    from app.core.config import settings

    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Analyze test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    inspection_id = create_resp.json()["id"]

    with patch.object(settings, "AI_PIPELINE_MODE", "stub"):
        resp = await client.post(
            f"/api/v1/inspections/{inspection_id}/analyze",
            headers={"Authorization": f"Bearer {inspector_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["pipeline_status"] == "DEV_STUB"
        assert "notice" in data
        assert data["overall_compliance_status"] == "NEEDS_REVIEW"


@pytest.mark.asyncio
async def test_reanalysis_is_idempotent(client, inspector_token):
    """Calling analyze twice on an inspection must cleanly replace prior results without duplicating rows."""
    from unittest.mock import MagicMock, patch
    import json
    from ai.pipeline.vision_pipeline import VisionPipeline
    from app.core.config import settings

    # 1. Create inspection
    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Idempotency test inspection"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    inspection_id = create_resp.json()["id"]

    # 2. Upload image
    img_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB"
    upload_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files=[("images", ("back_panel.jpg", img_content, "image/jpeg"))],
        data={"label": "BACK"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert upload_resp.status_code in (200, 201)

    # 3. Setup mock pipeline with a sample response
    sample_payload = {
        "commodity_name": {"value": "Dark Chocolate", "confidence": 0.95},
        "mrp": {"value": "₹ 100.00", "raw_text": "MRP Rs 100.00", "confidence": 0.98},
        "net_quantity": {"value": "50 g", "confidence": 0.90},
        "manufacturer_name": {"value": "Test Chocolates Ltd", "confidence": 0.92},
        "manufacturer_address": {"value": "123 Industrial Area, Pune 411001", "confidence": 0.90},
        "manufacturing_date": {"value": "2024-05", "confidence": 0.95},
        "best_before_date": {"value": "2025-05", "confidence": 0.85},
        "batch_number": {"value": "B-123", "confidence": 0.91},
        "consumer_care_info": {"value": "care@test.com", "confidence": 0.89},
        "country_of_origin": {"value": "India", "confidence": 0.96},
        "unit_sale_price": {"value": "₹ 2.00 / g", "confidence": 0.85},
        "ocr_regions": [
            {"text": "MRP Rs 100.00", "confidence": 0.95, "bounding_box": [10, 10, 100, 40]}
        ],
    }
    mock_pipeline = VisionPipeline()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(sample_payload)
    mock_client.models.generate_content.return_value = mock_resp
    mock_pipeline._client = mock_client

    with patch("app.api.inspections.get_pipeline", return_value=mock_pipeline):
        with patch.object(settings, "AI_PIPELINE_MODE", "vision"):
            # First analyze call
            resp1 = await client.post(
                f"/api/v1/inspections/{inspection_id}/analyze",
                headers={"Authorization": f"Bearer {inspector_token}"},
            )
            assert resp1.status_code == 200
            data1 = resp1.json()

            # Second analyze call (re-analysis)
            resp2 = await client.post(
                f"/api/v1/inspections/{inspection_id}/analyze",
                headers={"Authorization": f"Bearer {inspector_token}"},
            )
            assert resp2.status_code == 200
            data2 = resp2.json()

    # Verify counts in API response are identical
    assert len(data1["declarations"]) == len(data2["declarations"])
    assert len(data1["violations"]) == len(data2["violations"])
    assert len(data1["ocr_regions"]) == len(data2["ocr_regions"])

    # Verify counts in database detail view are stable (no row multiplication)
    detail_resp = await client.get(
        f"/api/v1/inspections/{inspection_id}",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["declarations"]) == len(data1["declarations"])
    assert len(detail["violations"]) == len(data1["violations"])
    assert len(detail["ocr_regions"]) == len(data1["ocr_regions"])

