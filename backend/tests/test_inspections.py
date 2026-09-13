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
    """The analyze endpoint should return a DEV_STUB result in Phase 1."""
    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Analyze test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    inspection_id = create_resp.json()["id"]

    resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/analyze",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["pipeline_status"] == "DEV_STUB"
    assert "notice" in data
    assert data["overall_compliance_status"] == "NEEDS_REVIEW"
