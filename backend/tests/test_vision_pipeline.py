"""
Tests for Phase 2+3 AI Vision Pipeline.
Validates extraction, deterministic normalization, missing field handling,
retry mechanisms, and integration with the inspection analyze endpoint.
"""
import json
import os
import pytest
from unittest.mock import MagicMock, patch

from ai.pipeline.vision_pipeline import (
    VisionPipeline,
    PipelineError,
    normalize_mrp,
    normalize_quantity,
    normalize_date,
)
from ai.pipeline.stub_pipeline import get_pipeline, StubPipeline
from app.core.config import settings


@pytest.fixture
def dummy_image(tmp_path):
    """Creates a temporary dummy image file for testing."""
    img_file = tmp_path / "label_test.jpg"
    img_file.write_bytes(b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB")
    return str(img_file)


@pytest.fixture
def valid_gemini_payload():
    """Generates a sample valid Gemini vision JSON response."""
    return {
        "commodity_name": {
            "value": "Whole Wheat Atta",
            "raw_text": "Whole Wheat Atta",
            "confidence": 0.95,
            "bounding_box": [10, 20, 210, 60]
        },
        "mrp": {
            "value": "₹ 245.00",
            "raw_text": "MRP Rs. 245.00 (incl. of all taxes)",
            "confidence": 0.98,
            "bounding_box": [30, 80, 230, 110]
        },
        "net_quantity": {
            "value": "5 kg",
            "raw_text": "Net Quantity: 5 kg",
            "confidence": 0.92,
            "bounding_box": [30, 120, 150, 150]
        },
        "manufacturer_name": {
            "value": "Pure Agro Foods Pvt Ltd",
            "raw_text": "Manufactured by Pure Agro Foods Pvt Ltd",
            "confidence": 0.90,
            "bounding_box": [10, 160, 310, 190]
        },
        "manufacturer_address": {
            "value": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "raw_text": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "confidence": 0.88,
            "bounding_box": [10, 200, 450, 230]
        },
        "manufacturing_date": {
            "value": "15/05/2024",
            "raw_text": "Mfg Date: 15/05/2024",
            "confidence": 0.94,
            "bounding_box": [50, 240, 200, 270]
        },
        "best_before_date": {
            "value": "04/05/2025",
            "raw_text": "Best Before: 04/05/2025",
            "confidence": 0.86,
            "bounding_box": [50, 280, 220, 310]
        },
        "batch_number": {
            "value": "BATCH-2024-X1",
            "raw_text": "Batch: BATCH-2024-X1",
            "confidence": 0.89,
            "bounding_box": [50, 320, 200, 350]
        },
        "consumer_care_info": {
            "value": "customercare@pureagro.com, 1800-123-4567",
            "raw_text": "For feedback: customercare@pureagro.com / 1800-123-4567",
            "confidence": 0.87,
            "bounding_box": [10, 360, 400, 390]
        },
        "country_of_origin": {
            "value": "India",
            "raw_text": "Country of Origin: India",
            "confidence": 0.96,
            "bounding_box": [10, 400, 180, 430]
        },
        "unit_sale_price": {
            "value": "₹ 49.00 / kg",
            "raw_text": "Unit Sale Price: ₹ 49.00 / kg",
            "confidence": 0.84,
            "bounding_box": [30, 440, 200, 470]
        },
        "ocr_regions": [
            {
                "text": "Whole Wheat Atta",
                "bounding_box": [10, 20, 210, 60],
                "confidence": 0.95
            },
            {
                "text": "MRP Rs. 245.00",
                "bounding_box": [30, 80, 230, 110],
                "confidence": 0.98
            }
        ]
    }


# ─── Test 1: Mocked Gemini response asserting correct parsing & normalization ──

def test_gemini_vision_parsing_and_normalization(dummy_image, valid_gemini_payload):
    """Asserts that Gemini vision output is parsed and normalized correctly."""
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(valid_gemini_payload)
    mock_client.models.generate_content.return_value = mock_response

    pipeline = VisionPipeline(client=mock_client)
    result = pipeline.analyze(dummy_image, "image-uuid-123")

    assert result.pipeline_status == "COMPLETED"
    assert result.image_id == "image-uuid-123"
    assert len(result.declarations) == 11
    assert len(result.ocr_regions) == 2

    # Verify MRP normalization (strip currency -> numeric float)
    mrp_decl = next(d for d in result.declarations if d.field_name == "mrp")
    assert mrp_decl.field_value == "245.0"
    assert result.metadata["normalized"]["mrp_value"] == 245.0
    assert mrp_decl.confidence == 0.98
    assert mrp_decl.bounding_box.x == 30.0
    assert mrp_decl.bounding_box.y == 80.0
    assert mrp_decl.bounding_box.width == 200.0  # 230 - 30
    assert mrp_decl.bounding_box.height == 30.0  # 110 - 80

    # Verify Net Quantity normalization
    qty_decl = next(d for d in result.declarations if d.field_name == "net_quantity")
    assert result.metadata["normalized"]["net_quantity"] == {"amount": 5.0, "unit": "kg"}

    # Verify Manufacturing Date (unambiguous day 15 > 12 -> ISO YYYY-MM-DD)
    mfg_decl = next(d for d in result.declarations if d.field_name == "manufacturing_date")
    assert mfg_decl.field_value == "2024-05-15"
    assert result.metadata["normalized"]["manufacturing_date"]["iso_date"] == "2024-05-15"
    assert result.metadata["normalized"]["manufacturing_date"]["needs_review"] is False

    # Verify Best Before Date (ambiguous 04/05/2025 -> needs_review is True)
    exp_decl = next(d for d in result.declarations if d.field_name == "best_before_date")
    assert result.metadata["normalized"]["best_before_date"]["needs_review"] is True

    # Verify mean confidence score
    assert result.confidence_score > 0.85


# ─── Test 2: Missing MRP yields value None, confidence 0.0 ─────────────────────

def test_missing_mrp_yields_none_and_zero_confidence(dummy_image, valid_gemini_payload):
    """Asserts that a missing MRP field yields value=None and confidence=0.0."""
    payload = valid_gemini_payload.copy()
    payload["mrp"] = {
        "value": None,
        "raw_text": None,
        "confidence": 0.0,
        "bounding_box": None,
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response

    pipeline = VisionPipeline(client=mock_client)
    result = pipeline.analyze(dummy_image, "image-uuid-missing-mrp")

    mrp_decl = next(d for d in result.declarations if d.field_name == "mrp")
    assert mrp_decl.field_value is None
    assert mrp_decl.confidence == 0.0
    assert result.metadata["normalized"]["mrp_value"] is None


# ─── Test 3: Malformed JSON raises PipelineError after one retry ───────────────

def test_malformed_json_raises_pipeline_error_after_retry(dummy_image):
    """Asserts that malformed JSON triggers one retry, then raises PipelineError."""
    mock_client = MagicMock()
    malformed_response = MagicMock()
    malformed_response.text = "NOT_A_VALID_JSON_STRING {{"
    mock_client.models.generate_content.return_value = malformed_response

    pipeline = VisionPipeline(client=mock_client)

    with pytest.raises(PipelineError) as exc_info:
        pipeline.analyze(dummy_image, "image-uuid-retry-test")

    assert "Malformed JSON response" in str(exc_info.value)
    # Verify it retried exactly once: total of 2 calls
    assert mock_client.models.generate_content.call_count == 2


# ─── Test 4: Factory routing ──────────────────────────────────────────────────

def test_get_pipeline_factory():
    """Asserts get_pipeline returns VisionPipeline when mode='vision', else StubPipeline."""
    v_pipe = get_pipeline("vision")
    assert isinstance(v_pipe, VisionPipeline)

    s_pipe = get_pipeline("stub")
    assert isinstance(s_pipe, StubPipeline)

    with patch.object(settings, "AI_PIPELINE_MODE", "vision"):
        auto_v_pipe = get_pipeline()
        assert isinstance(auto_v_pipe, VisionPipeline)


# ─── Test 5: Normalization unit tests ──────────────────────────────────────────

def test_normalization_functions():
    """Unit tests for mrp, quantity, and date normalizers."""
    # MRP
    assert normalize_mrp("MRP Rs. 499.50 (inclusive of all taxes)") == 499.5
    assert normalize_mrp("₹ 1,250.00") == 1250.0
    assert normalize_mrp("Rs. 100/-") == 100.0
    assert normalize_mrp(None, None) is None

    # Quantity
    assert normalize_quantity("Net Wt: 500 g") == {"amount": 500.0, "unit": "g"}
    assert normalize_quantity("1.5 kg") == {"amount": 1.5, "unit": "kg"}
    assert normalize_quantity("750 ml") == {"amount": 750.0, "unit": "ml"}
    assert normalize_quantity("10 units") == {"amount": 10.0, "unit": "nos"}
    assert normalize_quantity(None) is None

    # Date
    res_iso = normalize_date("2024-08-20")
    assert res_iso["iso_date"] == "2024-08-20"
    assert res_iso["needs_review"] is False

    res_month_name = normalize_date("MFG: 12-Oct-2024")
    assert res_month_name["iso_date"] == "2024-10-12"
    assert res_month_name["needs_review"] is False

    res_month_year = normalize_date("PKD 05/2024")
    assert res_month_year["iso_date"] == "2024-05"
    assert res_month_year["needs_review"] is False

    res_ambiguous = normalize_date("03/04/2024")
    assert res_ambiguous["needs_review"] is True


# ─── Test 6: Inspection analyze endpoint in vision mode ───────────────────────

@pytest.mark.asyncio
async def test_analyze_inspection_vision_mode(client, inspector_token, valid_gemini_payload, tmp_path):
    """Asserts POST /inspections/{id}/analyze persists declarations and ocr regions in vision mode."""
    # Create inspection
    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Vision analysis test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    inspection_id = create_resp.json()["id"]

    # Upload test image
    img_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB"
    upload_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files=[("images", ("front.jpg", img_content, "image/jpeg"))],
        data={"label": "FRONT"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert upload_resp.status_code in (200, 201)

    # Mock VisionPipeline
    mock_pipeline = VisionPipeline()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(valid_gemini_payload)
    mock_client.models.generate_content.return_value = mock_resp
    mock_pipeline._client = mock_client

    with patch("app.api.inspections.get_pipeline", return_value=mock_pipeline):
        with patch.object(settings, "AI_PIPELINE_MODE", "vision"):
            analyze_resp = await client.post(
                f"/api/v1/inspections/{inspection_id}/analyze",
                headers={"Authorization": f"Bearer {inspector_token}"},
            )
            assert analyze_resp.status_code == 200
            data = analyze_resp.json()

            assert data["pipeline_status"] == "COMPLETED"
            assert data["notice"] is None
            assert len(data["declarations"]) == 11
            assert len(data["ocr_regions"]) == 2
            assert data["confidence_score"] > 0.0

    # Fetch detail and verify persisted rows in DB
    detail_resp = await client.get(
        f"/api/v1/inspections/{inspection_id}",
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert detail_resp.status_code == 200
    detail = detail_resp.json()
    assert len(detail["declarations"]) == 11
    assert len(detail["ocr_regions"]) == 2
    assert detail["ai_pipeline_status"] == "COMPLETED"
    assert detail["ai_confidence_score"] > 0.0
