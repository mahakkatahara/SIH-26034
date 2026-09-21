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
    parse_bounding_box,
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
            "bounding_box": [20, 10, 60, 210]
        },
        "mrp": {
            "value": "₹ 245.00",
            "raw_text": "MRP Rs. 245.00 (incl. of all taxes)",
            "confidence": 0.98,
            "bounding_box": [80, 30, 110, 230]
        },
        "net_quantity": {
            "value": "5 kg",
            "raw_text": "Net Quantity: 5 kg",
            "confidence": 0.92,
            "bounding_box": [120, 30, 150, 150]
        },
        "manufacturer_name": {
            "value": "Pure Agro Foods Pvt Ltd",
            "raw_text": "Manufactured by Pure Agro Foods Pvt Ltd",
            "confidence": 0.90,
            "bounding_box": [160, 10, 190, 310]
        },
        "manufacturer_address": {
            "value": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "raw_text": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "confidence": 0.88,
            "bounding_box": [200, 10, 230, 450]
        },
        "manufacturing_date": {
            "value": "15/05/2024",
            "raw_text": "Mfg Date: 15/05/2024",
            "confidence": 0.94,
            "bounding_box": [240, 50, 270, 200]
        },
        "best_before_date": {
            "value": "04/05/2025",
            "raw_text": "Best Before: 04/05/2025",
            "confidence": 0.86,
            "bounding_box": [280, 50, 310, 220]
        },
        "batch_number": {
            "value": "BATCH-2024-X1",
            "raw_text": "Batch: BATCH-2024-X1",
            "confidence": 0.89,
            "bounding_box": [320, 50, 350, 200]
        },
        "consumer_care_info": {
            "value": "customercare@pureagro.com, 1800-123-4567",
            "raw_text": "For feedback: customercare@pureagro.com / 1800-123-4567",
            "confidence": 0.87,
            "bounding_box": [360, 10, 390, 400]
        },
        "country_of_origin": {
            "value": "India",
            "raw_text": "Country of Origin: India",
            "confidence": 0.96,
            "bounding_box": [400, 10, 430, 180]
        },
        "unit_sale_price": {
            "value": "₹ 49.00 / kg",
            "raw_text": "Unit Sale Price: ₹ 49.00 / kg",
            "confidence": 0.84,
            "bounding_box": [440, 30, 470, 200]
        },
        "ocr_regions": [
            {
                "text": "Whole Wheat Atta",
                "bounding_box": [20, 10, 60, 210],
                "confidence": 0.95
            },
            {
                "text": "MRP Rs. 245.00",
                "bounding_box": [80, 30, 110, 230],
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
    payload["ocr_regions"] = [
        r for r in valid_gemini_payload["ocr_regions"] if "MRP" not in r.get("text", "")
    ]

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


def test_parse_bounding_box_valid_coordinates():
    """Valid [ymin, xmin, ymax, xmax] normalized coordinates produce positive width and height."""
    # [ymin=100, xmin=200, ymax=500, xmax=600]
    bbox = parse_bounding_box([100, 200, 500, 600], conf=0.95)
    assert bbox is not None
    assert bbox.x == 200.0
    assert bbox.y == 100.0
    assert bbox.width == 400.0
    assert bbox.height == 400.0
    assert bbox.confidence == 0.95


def test_parse_bounding_box_gemini_normalized_scaled_to_image():
    """Gemini [ymin, xmin, ymax, xmax] normalized to 1000 scales accurately to image dimensions."""
    # [ymin=562, xmin=759, ymax=783, xmax=783] on 1280x720 image
    bbox = parse_bounding_box([562, 759, 783, 783], conf=0.90, img_width=1280, img_height=720)
    assert bbox is not None
    assert bbox.x == round(759 / 1000.0 * 1280, 2)  # 971.52
    assert bbox.y == round(562 / 1000.0 * 720, 2)   # 404.64
    assert bbox.width == round(24 / 1000.0 * 1280, 2) # 30.72
    assert bbox.height == round(221 / 1000.0 * 720, 2) # 159.12


def test_parse_bounding_box_inverted_rejected():
    """Inverted coordinates (ymin >= ymax or xmin >= xmax) must be rejected and return None."""
    # Inverted y: ymin > ymax
    assert parse_bounding_box([500, 200, 100, 600], conf=0.88) is None
    # Inverted x: xmin > xmax
    assert parse_bounding_box([100, 600, 500, 200], conf=0.88) is None
    # Both inverted
    assert parse_bounding_box([500, 600, 100, 200], conf=0.88) is None


def test_parse_bounding_box_degenerate_rejected():
    """Degenerate bounding boxes (zero width or zero height or empty) must return None."""
    # Zero height: ymin == ymax
    assert parse_bounding_box([561.0, 761.0, 561.0, 783.0], conf=0.90) is None
    # Zero width: xmin == xmax
    assert parse_bounding_box([561.0, 761.0, 783.0, 761.0], conf=0.90) is None
    # Zero width and height (single point)
    assert parse_bounding_box([500.0, 500.0, 500.0, 500.0], conf=0.90) is None
    # None or malformed coords
    assert parse_bounding_box(None) is None
    assert parse_bounding_box([]) is None
    assert parse_bounding_box([10, 20]) is None
    assert parse_bounding_box([10, 20, 30]) is None
    assert parse_bounding_box([10, 20, 30, 40, 50]) is None


def test_parse_bounding_box_out_of_range_rejected():
    """Coordinates outside [0, 1000] must be rejected, return None, and log a warning."""
    from unittest.mock import patch

    with patch("ai.pipeline.vision_pipeline.logger.warning") as mock_warn:
        # Negative coordinates
        assert parse_bounding_box([-10, 200, 500, 600], conf=0.9) is None
        assert mock_warn.called
        assert "out of [0, 1000] range" in mock_warn.call_args[0][0]

        mock_warn.reset_mock()
        assert parse_bounding_box([100, -5, 500, 600], conf=0.9) is None
        assert mock_warn.called
        assert "out of [0, 1000] range" in mock_warn.call_args[0][0]

        # Exceeding 1000
        mock_warn.reset_mock()
        assert parse_bounding_box([100, 200, 1005, 600], conf=0.9) is None
        assert mock_warn.called
        assert "out of [0, 1000] range" in mock_warn.call_args[0][0]

        mock_warn.reset_mock()
        assert parse_bounding_box([100, 200, 500, 1200], conf=0.9) is None
        assert mock_warn.called
        assert "out of [0, 1000] range" in mock_warn.call_args[0][0]


def test_package_label_analysis_schema_requires_all_statutory_fields():
    """All 11 declaration fields must be in the required array of PackageLabelAnalysis schema."""
    from pydantic import ValidationError
    from ai.pipeline.vision_pipeline import PackageLabelAnalysis

    schema = PackageLabelAnalysis.model_json_schema()
    required = schema.get("required", [])

    expected_fields = [
        "commodity_name",
        "mrp",
        "net_quantity",
        "manufacturer_name",
        "manufacturer_address",
        "manufacturing_date",
        "best_before_date",
        "batch_number",
        "consumer_care_info",
        "country_of_origin",
        "unit_sale_price",
    ]

    for f in expected_fields:
        assert f in required, f"Field '{f}' must be required in PackageLabelAnalysis schema"

    # Omitting any required field must raise ValidationError
    with pytest.raises(ValidationError):
        PackageLabelAnalysis.model_validate({"mrp": {"value": "10.0"}})

    # Providing all fields with null/0.0 values must be valid
    valid_null_payload = {
        f: {"value": None, "raw_text": None, "confidence": 0.0, "bounding_box": []}
        for f in expected_fields
    }
    model = PackageLabelAnalysis.model_validate(valid_null_payload)
    assert model.mrp.value is None
    assert model.mrp.confidence == 0.0


def test_option_b_safety_net_ocr_keyword_overrides_absent_to_unreadable(dummy_image, valid_gemini_payload):
    """When a mandatory field value is null / absent but an OCR region has matching keywords, override state to 'unreadable'."""
    payload = dict(valid_gemini_payload)
    # Set mrp to absent with null value
    payload["mrp"] = {
        "value": None,
        "raw_text": None,
        "confidence": 0.0,
        "bounding_box": [],
        "state": "absent",
    }
    payload["ocr_regions"] = [
        {
            "text": "MRP Rs. 245.00 (incl. of all taxes)",
            "bounding_box": [80, 30, 110, 230],
            "confidence": 0.94,
        }
    ]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response

    pipeline = VisionPipeline(client=mock_client)
    result = pipeline.analyze(dummy_image, "image-uuid-safety-net")

    mrp_decl = next(d for d in result.declarations if d.field_name == "mrp")
    assert mrp_decl.state == "unreadable"
    assert mrp_decl.raw_text == "MRP Rs. 245.00 (incl. of all taxes)"
    assert mrp_decl.confidence == 0.94


def test_option_b_safety_net_ocr_proximity_overrides_absent_to_unreadable(dummy_image, valid_gemini_payload):
    """When a mandatory field value is null but an OCR region overlaps or is proximate to its bounding box, override state to 'unreadable'."""
    payload = dict(valid_gemini_payload)
    # Set net_quantity to null value, but with bounding box
    payload["net_quantity"] = {
        "value": None,
        "raw_text": None,
        "confidence": 0.0,
        "bounding_box": [120, 30, 150, 150],
        "state": "absent",
    }
    # OCR region has arbitrary text with no statutory keywords, but overlaps the bounding box
    payload["ocr_regions"] = [
        {
            "text": "unreadable smeared print",
            "bounding_box": [122, 35, 148, 145],
            "confidence": 0.88,
        }
    ]

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = json.dumps(payload)
    mock_client.models.generate_content.return_value = mock_response

    pipeline = VisionPipeline(client=mock_client)
    result = pipeline.analyze(dummy_image, "image-uuid-proximity-net")

    qty_decl = next(d for d in result.declarations if d.field_name == "net_quantity")
    assert qty_decl.state == "unreadable"
    assert qty_decl.confidence >= 0.88




