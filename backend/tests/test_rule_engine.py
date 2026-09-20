"""
Tests for Phase 4 Deterministic Rule Engine Validators and Aggregation.
Verifies:
- Individual handlers: presence_check, format_check, unit_check,
  conditional_check, visibility_check, font_size_check
- Aggregation semantics:
  - fully compliant label => COMPLIANT
  - missing MRP => NON_COMPLIANT citing MRP-001
  - low confidence compliant label => NEEDS_REVIEW
  - 4 missing fields => NEEDS_REVIEW (not NON_COMPLIANT)
  - medium/low severity issues => WARNING
  - NOT_APPLICABLE does not affect overall status
"""
import pytest
from engine import (
    RuleEngine,
    RuleDefinition,
    RuleEvaluationStatus,
    ComplianceStatus,
    ViolationSeverity,
)


@pytest.fixture
def rule_engine():
    """Initializes the rule engine with default rules.json."""
    return RuleEngine()


@pytest.fixture
def compliant_declarations():
    """Returns a full set of compliant declarations covering all mandatory fields."""
    return [
        {
            "declaration_id": "decl-1",
            "field_name": "commodity_name",
            "field_value": "Whole Wheat Atta",
            "raw_text": "Whole Wheat Atta",
            "confidence": 0.98,
            "bounding_box": [100, 50, 400, 80],
        },
        {
            "declaration_id": "decl-2",
            "field_name": "mrp",
            "field_value": "450.0",
            "raw_text": "MRP Rs. 450.00 (inclusive of all taxes)",
            "confidence": 0.99,
            "bounding_box": [100, 90, 350, 120],
        },
        {
            "declaration_id": "decl-3",
            "field_name": "net_quantity",
            "field_value": "5 kg",
            "raw_text": "Net Quantity: 5 kg",
            "confidence": 0.95,
            "bounding_box": [100, 130, 250, 160],
        },
        {
            "declaration_id": "decl-4",
            "field_name": "manufacturer_name",
            "field_value": "Pure Agro Foods Private Limited",
            "raw_text": "Manufactured by Pure Agro Foods Private Limited",
            "confidence": 0.96,
            "bounding_box": [100, 170, 450, 200],
        },
        {
            "declaration_id": "decl-5",
            "field_name": "manufacturer_address",
            "field_value": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "raw_text": "Plot 45, MIDC, Pune 411019, Maharashtra",
            "confidence": 0.94,
            "bounding_box": [100, 210, 500, 240],
        },
        {
            "declaration_id": "decl-6",
            "field_name": "manufacturing_date",
            "field_value": "2024-10",
            "raw_text": "Mfg Date: 10/2024",
            "confidence": 0.97,
            "bounding_box": [100, 250, 300, 280],
        },
        {
            "declaration_id": "decl-7",
            "field_name": "consumer_care_info",
            "field_value": "care@pureagro.com, Ph: 1800-123-456",
            "raw_text": "Consumer Care: care@pureagro.com, Ph: 1800-123-456",
            "confidence": 0.95,
            "bounding_box": [100, 290, 450, 320],
        },
        {
            "declaration_id": "decl-8",
            "field_name": "batch_number",
            "field_value": "B-2024-99",
            "raw_text": "Batch No: B-2024-99",
            "confidence": 0.97,
            "bounding_box": [100, 330, 280, 355],
        },
    ]


# ─── Handler 1: presence_check ────────────────────────────────────────────────

def test_presence_check(rule_engine):
    """Verifies that presence_check requires non-null, stripped length > 0."""
    rule = RuleDefinition(
        rule_id="TEST-PRESENCE",
        field="commodity_name",
        mandatory=True,
        severity=ViolationSeverity.HIGH,
        description="Commodity name must be present",
        validation_logic={"type": "presence_check", "field": "commodity_name"},
    )

    # Valid non-empty presence
    res_pass = rule_engine._check_presence(
        rule,
        {"field_name": "commodity_name", "field_value": "Basmati Rice"}
    )
    assert res_pass.status == RuleEvaluationStatus.PASSED
    assert res_pass.violation is None

    # Missing declaration (None)
    res_missing = rule_engine._check_presence(rule, None)
    assert res_missing.status == RuleEvaluationStatus.FAILED
    assert res_missing.violation is not None
    assert res_missing.violation.rule_id == "TEST-PRESENCE"
    assert res_missing.violation.observed_value is None

    # Empty string or whitespace
    res_empty = rule_engine._check_presence(
        rule,
        {"field_name": "commodity_name", "field_value": "   "}
    )
    assert res_empty.status == RuleEvaluationStatus.FAILED
    assert res_empty.violation is not None


# ─── Handler 2: format_check ──────────────────────────────────────────────────

def test_format_check(rule_engine):
    """Verifies regex pattern matching honouring case_insensitive flag."""
    rule = RuleDefinition(
        rule_id="MRP-002",
        field="mrp",
        mandatory=True,
        severity=ViolationSeverity.HIGH,
        description="MRP must be declared as 'MRP Rs.' or 'MRP ₹' followed by the inclusive price",
        validation_logic={
            "type": "format_check",
            "pattern": r"MRP\s*(Rs\.?|₹)\s*[0-9]+",
            "case_insensitive": True,
        },
    )

    # Matches with standard MRP Rs.
    res_1 = rule_engine._check_format(
        rule,
        {"raw_text": "MRP Rs. 245 (inclusive of all taxes)", "field_value": "245"}
    )
    assert res_1.status == RuleEvaluationStatus.PASSED

    # Matches with currency symbol case-insensitively
    res_2 = rule_engine._check_format(
        rule,
        {"raw_text": "mrp ₹ 50", "field_value": "50"}
    )
    assert res_2.status == RuleEvaluationStatus.PASSED

    # Fails when required prefix is missing
    res_fail = rule_engine._check_format(
        rule,
        {"raw_text": "Price: 245", "field_value": "245"}
    )
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation is not None
    assert res_fail.violation.rule_id == "MRP-002"
    assert "Price: 245" in str(res_fail.violation.observed_value)


# ─── Handler 3: unit_check ────────────────────────────────────────────────────

def test_unit_check(rule_engine):
    """Verifies unit_check with normalization of variants (gm/g/gram, ltr/litre/l, etc.)."""
    rule = RuleDefinition(
        rule_id="NQ-002",
        field="net_quantity",
        mandatory=True,
        severity=ViolationSeverity.MEDIUM,
        description="Net quantity must be expressed in standard legal units",
        validation_logic={
            "type": "unit_check",
            "allowed_units": ["g", "gm", "gram", "kg", "kilogram", "ml", "l", "ltr", "litre", "nos"],
        },
    )

    # Test normalized variants: gm -> g, gram -> g, ltr -> l, kg -> kg
    for valid_unit_text in ["500 g", "500 gm", "500 gram", "1 kg", "200 ml", "1 ltr", "1 litre", "10 nos"]:
        res = rule_engine._check_unit(
            rule,
            {"field_name": "net_quantity", "field_value": valid_unit_text, "declaration_id": "d-1"}
        )
        assert res.status == RuleEvaluationStatus.PASSED, f"Failed for valid unit: {valid_unit_text}"

    # Test invalid / unauthorized units
    for invalid_unit_text in ["500 ounces", "10 lbs", "2 bottles", "5 boxes"]:
        res = rule_engine._check_unit(
            rule,
            {"field_name": "net_quantity", "field_value": invalid_unit_text, "declaration_id": "d-2"}
        )
        assert res.status == RuleEvaluationStatus.FAILED, f"Should fail for: {invalid_unit_text}"
        assert res.violation is not None
        assert res.violation.severity == ViolationSeverity.MEDIUM
        assert res.violation.declaration_id == "d-2"


# ─── Handler 4: conditional_check ─────────────────────────────────────────────

def test_conditional_check(rule_engine):
    """Verifies conditional_check evaluates when condition holds, else returns NOT_APPLICABLE."""
    rule_perishable = RuleDefinition(
        rule_id="DATE-002",
        field="best_before_date",
        mandatory=False,
        severity=ViolationSeverity.MEDIUM,
        description="Best before date required for perishable commodities",
        validation_logic={
            "type": "conditional_check",
            "condition": "is_perishable",
            "field": "best_before_date",
        },
    )

    # Case A: is_perishable=False -> NOT_APPLICABLE (even if field is absent)
    res_not_app = rule_engine._check_conditional(
        rule_perishable,
        decl=None,
        product_context={"is_perishable": False}
    )
    assert res_not_app.status == RuleEvaluationStatus.NOT_APPLICABLE
    assert res_not_app.violation is None

    # Case B: is_perishable=True and field is present -> PASSED
    res_pass = rule_engine._check_conditional(
        rule_perishable,
        decl={"field_name": "best_before_date", "field_value": "12/2026"},
        product_context={"is_perishable": True}
    )
    assert res_pass.status == RuleEvaluationStatus.PASSED

    # Case C: is_perishable=True but field is absent -> FAILED
    res_fail = rule_engine._check_conditional(
        rule_perishable,
        decl=None,
        product_context={"is_perishable": True}
    )
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation is not None
    assert res_fail.violation.rule_id == "DATE-002"

    # Case D: is_imported condition test
    rule_import = RuleDefinition(
        rule_id="COO-001",
        field="country_of_origin",
        mandatory=False,
        severity=ViolationSeverity.MEDIUM,
        description="Country of origin required for imported goods",
        validation_logic={
            "type": "conditional_check",
            "condition": "is_imported",
            "field": "country_of_origin",
        },
    )
    assert rule_engine._check_conditional(
        rule_import, None, {"is_imported": False}
    ).status == RuleEvaluationStatus.NOT_APPLICABLE


# ─── Handler 5: visibility_check ──────────────────────────────────────────────

def test_visibility_check(rule_engine):
    """Verifies that visibility_check maps low confidence / obscured to NEEDS_REVIEW, never NON_COMPLIANT."""
    rule = RuleDefinition(
        rule_id="MRP-003",
        field="mrp",
        mandatory=True,
        severity=ViolationSeverity.MEDIUM,
        description="MRP must not be obscured",
        validation_logic={"type": "visibility_check", "field": "mrp"},
    )

    # Case A: Clear and confident -> PASSED
    res_clear = rule_engine._check_visibility(
        rule,
        {"field_name": "mrp", "confidence": 0.95, "is_obscured": False},
        confidence_threshold=0.75,
    )
    assert res_clear.status == RuleEvaluationStatus.PASSED

    # Case B: Obscured flag -> NEEDS_REVIEW (never FAILED / NON_COMPLIANT)
    res_obscured = rule_engine._check_visibility(
        rule,
        {"field_name": "mrp", "confidence": 0.95, "is_obscured": True},
        confidence_threshold=0.75,
    )
    assert res_obscured.status == RuleEvaluationStatus.NEEDS_REVIEW
    assert res_obscured.violation is None  # Does not register as a non-compliance violation

    # Case C: Low confidence (0.60 < 0.75) -> NEEDS_REVIEW
    res_low_conf = rule_engine._check_visibility(
        rule,
        {"field_name": "mrp", "confidence": 0.60, "is_obscured": False},
        confidence_threshold=0.75,
    )
    assert res_low_conf.status == RuleEvaluationStatus.NEEDS_REVIEW


# ─── Handler 6: font_size_check (Sprint 6/7 Stub) ─────────────────────────────

def test_font_size_check(rule_engine):
    """Verifies font_size_check returns NOT_APPLICABLE with explicit Sprint 7 message."""
    rule = RuleDefinition(
        rule_id="FONT-001",
        field="font_size",
        mandatory=True,
        severity=ViolationSeverity.MEDIUM,
        description="Font size check",
        validation_logic={"type": "font_size_check", "min_height_mm": 1.0},
    )
    res = rule_engine._check_font_size(rule, None)
    assert res.status == RuleEvaluationStatus.NOT_APPLICABLE
    assert "font analysis pending (Sprint 7)" in res.reason


# ─── Aggregation Test 1: Fully Compliant Label ────────────────────────────────

def test_evaluate_fully_compliant_label(rule_engine, compliant_declarations):
    """Asserts that a label with all mandatory rules passing evaluates to COMPLIANT."""
    result = rule_engine.evaluate(
        declarations=compliant_declarations,
        product_category=None,
        product_context={},
        overall_confidence=0.96,
        confidence_threshold=0.75,
    )
    assert result.status == ComplianceStatus.COMPLIANT
    assert len(result.violations) == 0
    assert len(result.warnings) == 0


# ─── Aggregation Test 2: Missing MRP => NON_COMPLIANT citing MRP-001 ──────────

def test_evaluate_missing_mrp_non_compliant(rule_engine, compliant_declarations):
    """Asserts that missing MRP alone fails mandatory HIGH rule MRP-001 => NON_COMPLIANT."""
    # Remove MRP declaration
    decls_no_mrp = [d for d in compliant_declarations if d["field_name"] != "mrp"]

    result = rule_engine.evaluate(
        declarations=decls_no_mrp,
        product_category=None,
        product_context={},
        overall_confidence=0.95,
        confidence_threshold=0.75,
    )
    assert result.status == ComplianceStatus.NON_COMPLIANT
    assert len(result.violations) >= 1

    # Specifically verify MRP-001 violation is present
    mrp_violation = next((v for v in result.violations if v.rule_id == "MRP-001"), None)
    assert mrp_violation is not None
    assert mrp_violation.field == "mrp"
    assert mrp_violation.severity == ViolationSeverity.HIGH
    assert "Legal Metrology" in str(mrp_violation.legal_reference)


# ─── Aggregation Test 3: Low Confidence Compliant Label => NEEDS_REVIEW ───────

def test_evaluate_low_confidence_compliant_label(rule_engine, compliant_declarations):
    """Asserts that overall confidence below threshold downgrades status to NEEDS_REVIEW."""
    result = rule_engine.evaluate(
        declarations=compliant_declarations,
        product_category=None,
        product_context={},
        overall_confidence=0.62,  # < 0.75 threshold
        confidence_threshold=0.75,
    )
    assert result.status == ComplianceStatus.NEEDS_REVIEW
    assert any("below verification threshold" in note for note in result.notes)


# ─── Aggregation Test 4: 4 Missing Fields => NEEDS_REVIEW not NON_COMPLIANT ───

def test_evaluate_four_missing_fields_needs_review(rule_engine, compliant_declarations):
    """
    Asserts that 4 absent mandatory fields downgrade to NEEDS_REVIEW,
    protecting against false non-compliance due to unphotographed package panels.
    """
    # Keep only commodity_name and net_quantity (4 mandatory fields absent: mrp, mfr_name, mfr_address, mfg_date)
    sparse_decls = [
        d for d in compliant_declarations
        if d["field_name"] in ("commodity_name", "net_quantity")
    ]

    result = rule_engine.evaluate(
        declarations=sparse_decls,
        product_category=None,
        product_context={},
        overall_confidence=0.98,
        confidence_threshold=0.75,
    )
    assert result.status == ComplianceStatus.NEEDS_REVIEW
    assert any("unphotographed package panels" in note for note in result.notes)


# ─── Aggregation Test 5: Medium/Low Failures => WARNING ────────────────────────

def test_evaluate_medium_low_failures_warning(rule_engine, compliant_declarations):
    """Asserts that when all HIGH rules pass but a MEDIUM rule fails, status is WARNING."""
    # Modify net_quantity to have an unauthorized unit
    decls_bad_unit = []
    for d in compliant_declarations:
        if d["field_name"] == "net_quantity":
            decls_bad_unit.append({**d, "field_value": "500 ounces"})
        else:
            decls_bad_unit.append(d)

    result = rule_engine.evaluate(
        declarations=decls_bad_unit,
        product_category=None,
        product_context={},
        overall_confidence=0.95,
        confidence_threshold=0.75,
    )
    assert result.status == ComplianceStatus.WARNING
    assert len(result.warnings) >= 1
    assert any(w.rule_id == "NQ-002" for w in result.warnings)


# ─── Integration Test: Endpoint Analyze Missing MRP => NON_COMPLIANT ──────────

@pytest.mark.asyncio
async def test_analyze_endpoint_missing_mrp_non_compliant(client, inspector_token):
    """
    Asserts that POST /api/v1/inspections/{id}/analyze evaluates through the rule engine,
    detects missing MRP alone, returns overall_compliance_status=NON_COMPLIANT,
    and returns an open violation citing Rule 6(1)(f) and MRP-001.
    """
    from unittest.mock import patch, MagicMock
    import json
    from app.core.config import settings
    from ai.pipeline.vision_pipeline import VisionPipeline

    # 1. Create inspection
    create_resp = await client.post(
        "/api/v1/inspections",
        json={"remarks": "Missing MRP integration test"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert create_resp.status_code == 201
    inspection_id = create_resp.json()["id"]

    # 2. Upload dummy image
    img_content = b"\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00`\x00`\x00\x00\xFF\xDB"
    upload_resp = await client.post(
        f"/api/v1/inspections/{inspection_id}/images",
        files=[("images", ("label.jpg", img_content, "image/jpeg"))],
        data={"label": "FRONT"},
        headers={"Authorization": f"Bearer {inspector_token}"},
    )
    assert upload_resp.status_code in (200, 201)

    # 3. Mock vision pipeline returning payload without MRP
    payload_missing_mrp = {
        "commodity_name": {"value": "Basmati Rice", "raw_text": "Basmati Rice", "confidence": 0.98},
        "mrp": {"value": None, "raw_text": None, "confidence": 0.0},
        "net_quantity": {"value": "5 kg", "raw_text": "Net Quantity: 5 kg", "confidence": 0.96},
        "manufacturer_name": {"value": "Agro Ltd", "raw_text": "Agro Ltd", "confidence": 0.95},
        "manufacturer_address": {"value": "Phase 1, Delhi 110001", "raw_text": "Phase 1, Delhi 110001", "confidence": 0.95},
        "manufacturing_date": {"value": "10/2024", "raw_text": "10/2024", "confidence": 0.96},
        "consumer_care_info": {"value": "care@agro.com", "raw_text": "care@agro.com", "confidence": 0.95},
        "best_before_date": {"value": None, "raw_text": None, "confidence": 0.0},
        "batch_number": {"value": "B-12", "raw_text": "B-12", "confidence": 0.95},
        "country_of_origin": {"value": "India", "raw_text": "India", "confidence": 0.95},
        "unit_sale_price": {"value": "Rs. 90/kg", "raw_text": "Rs. 90/kg", "confidence": 0.95},
        "ocr_regions": [],
    }

    mock_pipeline = VisionPipeline()
    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(payload_missing_mrp)
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

            # Verify deterministic rule engine evaluation output
            assert data["pipeline_status"] == "COMPLETED"
            assert data["overall_compliance_status"] == "NON_COMPLIANT"
            assert len(data["violations"]) >= 1

            # Verify violation carries expected attributes
            mrp_violation = next((v for v in data["violations"] if "MRP" in v["description"] or "mrp" in v.get("description", "").lower()), None)
            assert mrp_violation is not None
            assert mrp_violation["severity"] == "HIGH"
            assert mrp_violation["status"] == "OPEN"
            assert "Legal Metrology" in str(mrp_violation["legal_reference"])


# ─── New Rules & Placement & Package Type Tests ───────────────────────────────

def test_name_001_commodity_name_presence(rule_engine):
    """Verifies NAME-001: commodity_name presence check with HIGH severity."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "NAME-001")
    assert rule.mandatory is True
    assert rule.severity == ViolationSeverity.HIGH
    assert rule.package_type == "any"

    # Present -> PASSED
    res_pass = rule_engine._check_presence(
        rule, {"field_name": "commodity_name", "field_value": "Wheat Flour"}
    )
    assert res_pass.status == RuleEvaluationStatus.PASSED

    # Absent -> FAILED
    res_fail = rule_engine._check_presence(rule, None)
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation.rule_id == "NAME-001"
    assert res_fail.violation.severity == ViolationSeverity.HIGH


def test_batch_001_batch_number_presence(rule_engine):
    """Verifies BATCH-001: batch_number presence check with MEDIUM severity."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "BATCH-001")
    assert rule.mandatory is True
    assert rule.severity == ViolationSeverity.MEDIUM
    assert rule.package_type == "retail"

    # Present -> PASSED
    res_pass = rule_engine._check_presence(
        rule, {"field_name": "batch_number", "field_value": "LOT-2024-X"}
    )
    assert res_pass.status == RuleEvaluationStatus.PASSED

    # Absent -> FAILED
    res_fail = rule_engine._check_presence(rule, None)
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation.rule_id == "BATCH-001"
    assert res_fail.violation.severity == ViolationSeverity.MEDIUM


def test_usp_001_conditional_check(rule_engine):
    """Verifies USP-001: unit sale price conditional check on requires_usp."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "USP-001")
    assert rule.mandatory is False
    assert rule.package_type == "retail"

    # Case A: requires_usp is False -> NOT_APPLICABLE
    res_na = rule_engine._check_conditional(
        rule, decl=None, product_context={"requires_usp": False}
    )
    assert res_na.status == RuleEvaluationStatus.NOT_APPLICABLE

    # Case B: requires_usp is True and field present -> PASSED
    res_pass = rule_engine._check_conditional(
        rule,
        decl={"field_name": "unit_sale_price", "field_value": "₹ 50.00 / kg"},
        product_context={"requires_usp": True},
    )
    assert res_pass.status == RuleEvaluationStatus.PASSED

    # Case C: requires_usp is True but field absent -> FAILED
    res_fail = rule_engine._check_conditional(
        rule, decl=None, product_context={"requires_usp": True}
    )
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation.rule_id == "USP-001"


def test_tax_001_inclusive_of_taxes_format(rule_engine):
    """Verifies TAX-001: MRP must state inclusive of all taxes."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "TAX-001")
    assert rule.severity == ViolationSeverity.MEDIUM

    # Matches "inclusive of all taxes"
    decl_incl = {
        "field_name": "mrp",
        "raw_text": "MRP Rs. 500.00 (inclusive of all taxes)",
        "field_value": "500.00",
    }
    assert rule_engine._check_format(rule, decl_incl).status == RuleEvaluationStatus.PASSED

    # Matches "incl. of all taxes"
    decl_abbr = {
        "field_name": "mrp",
        "raw_text": "MRP ₹ 250/- (incl. of all taxes)",
        "field_value": "250",
    }
    assert rule_engine._check_format(rule, decl_abbr).status == RuleEvaluationStatus.PASSED

    # Matches "incl. all taxes"
    decl_short = {
        "field_name": "mrp",
        "raw_text": "₹99 incl. all taxes",
        "field_value": "99",
    }
    assert rule_engine._check_format(rule, decl_short).status == RuleEvaluationStatus.PASSED

    # Non-matching tax wording -> FAILED
    decl_no_tax = {
        "field_name": "mrp",
        "raw_text": "MRP Rs. 100.00",
        "field_value": "100.00",
    }
    res_fail = rule_engine._check_format(rule, decl_no_tax)
    assert res_fail.status == RuleEvaluationStatus.FAILED
    assert res_fail.violation.rule_id == "TAX-001"


def test_place_001_placement_grouped_passes(rule_engine):
    """Verifies PLACE-001: clustered bounding boxes on single panel evaluate to PASSED."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "PLACE-001")
    decls_by_field = {
        "commodity_name": {
            "field_name": "commodity_name", "field_value": "Atta", "bounding_box": [100, 50, 400, 80]
        },
        "mrp": {
            "field_name": "mrp", "field_value": "50", "bounding_box": [100, 90, 300, 120]
        },
        "net_quantity": {
            "field_name": "net_quantity", "field_value": "1 kg", "bounding_box": [100, 130, 250, 160]
        },
    }
    res = rule_engine._check_placement(rule, decls_by_field, list(decls_by_field.values()))
    assert res.status == RuleEvaluationStatus.PASSED
    assert res.violation is None


def test_place_001_placement_split_panels_fails(rule_engine):
    """Verifies PLACE-001: declarations across distinct panels/disjoint coordinates FAIL."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "PLACE-001")

    # Case A: Explicit multi-panel metadata
    decls_multi_panel = {
        "commodity_name": {
            "field_name": "commodity_name", "field_value": "Atta", "panel": "FRONT"
        },
        "mrp": {
            "field_name": "mrp", "field_value": "50", "panel": "BACK"
        },
    }
    res_panel = rule_engine._check_placement(rule, decls_multi_panel, list(decls_multi_panel.values()))
    assert res_panel.status == RuleEvaluationStatus.FAILED
    assert res_panel.violation is not None
    assert res_panel.violation.rule_id == "PLACE-001"

    # Case B: Disjoint coordinates across image (e.g. front left panel vs far back right panel)
    decls_disjoint = {
        "commodity_name": {
            "field_name": "commodity_name", "field_value": "Atta", "bounding_box": [50, 50, 200, 100]
        },
        "mrp": {
            "field_name": "mrp", "field_value": "50", "bounding_box": [900, 50, 1050, 100]
        },
    }
    res_disjoint = rule_engine._check_placement(rule, decls_disjoint, list(decls_disjoint.values()))
    assert res_disjoint.status == RuleEvaluationStatus.FAILED
    assert res_disjoint.violation.rule_id == "PLACE-001"


def test_place_001_placement_no_boxes_not_applicable(rule_engine):
    """Verifies PLACE-001 returns NOT_APPLICABLE when no coordinates exist."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "PLACE-001")
    decls_no_boxes = {
        "commodity_name": {"field_name": "commodity_name", "field_value": "Atta"},
        "mrp": {"field_name": "mrp", "field_value": "50"},
    }
    res = rule_engine._check_placement(rule, decls_no_boxes, list(decls_no_boxes.values()))
    assert res.status == RuleEvaluationStatus.NOT_APPLICABLE


def test_wholesale_package_evaluation_compliant(rule_engine):
    """
    Verifies wholesale packages require only 3 declarations under Rule 24:
    name/address of mfr, net quantity, and commodity name.
    Lacking MRP, manufacturing date, and CC info evaluates to COMPLIANT.
    """
    wholesale_declarations = [
        {
            "declaration_id": "ws-1",
            "field_name": "commodity_name",
            "field_value": "Industrial Flour 50kg Sack",
            "confidence": 0.98,
        },
        {
            "declaration_id": "ws-2",
            "field_name": "net_quantity",
            "field_value": "50 kg",
            "confidence": 0.96,
        },
        {
            "declaration_id": "ws-3",
            "field_name": "manufacturer_name",
            "field_value": "Agro Millers Pvt Ltd",
            "confidence": 0.97,
        },
        {
            "declaration_id": "ws-4",
            "field_name": "manufacturer_address",
            "field_value": "Plot 10, Industrial Estate, Nagpur 440001",
            "confidence": 0.95,
        },
    ]

    result = rule_engine.evaluate(
        declarations=wholesale_declarations,
        package_type="wholesale",
        overall_confidence=0.96,
    )
    assert result.status == ComplianceStatus.COMPLIANT
    assert len(result.violations) == 0
    assert len(result.warnings) == 0
    assert result.evaluated_rules == 5  # NAME-001, NQ-001, NQ-002, MFR-001, MFR-002


def test_wholesale_package_missing_commodity_name_fails(rule_engine):
    """Verifies wholesale package lacking commodity name fails mandatory NAME-001 rule."""
    wholesale_no_name = [
        {
            "declaration_id": "ws-2",
            "field_name": "net_quantity",
            "field_value": "50 kg",
            "confidence": 0.96,
        },
        {
            "declaration_id": "ws-3",
            "field_name": "manufacturer_name",
            "field_value": "Agro Millers Pvt Ltd",
            "confidence": 0.97,
        },
        {
            "declaration_id": "ws-4",
            "field_name": "manufacturer_address",
            "field_value": "Plot 10, Industrial Estate, Nagpur 440001",
            "confidence": 0.95,
        },
    ]

    result = rule_engine.evaluate(
        declarations=wholesale_no_name,
        package_type="wholesale",
        overall_confidence=0.96,
    )
    assert result.status == ComplianceStatus.NON_COMPLIANT
    assert any(v.rule_id == "NAME-001" for v in result.violations)


def test_wholesale_package_exempt_from_mrp_vs_retail(rule_engine):
    """
    Demonstrates package_type discrimination:
    - Same declarations lacking MRP are COMPLIANT for wholesale.
    - But NON_COMPLIANT for retail (fails mandatory MRP-001).
    """
    declarations_lacking_mrp = [
        {
            "declaration_id": "d-1",
            "field_name": "commodity_name",
            "field_value": "Refined Sugar",
            "confidence": 0.98,
        },
        {
            "declaration_id": "d-2",
            "field_name": "net_quantity",
            "field_value": "25 kg",
            "confidence": 0.96,
        },
        {
            "declaration_id": "d-3",
            "field_name": "manufacturer_name",
            "field_value": "Sugar Mills Ltd",
            "confidence": 0.97,
        },
        {
            "declaration_id": "d-4",
            "field_name": "manufacturer_address",
            "field_value": "Sugar Town, Kolhapur 416001",
            "confidence": 0.95,
        },
    ]

    # Wholesale evaluation -> COMPLIANT (MRP not required)
    ws_result = rule_engine.evaluate(
        declarations=declarations_lacking_mrp,
        package_type="wholesale",
        overall_confidence=0.96,
    )
    assert ws_result.status == ComplianceStatus.COMPLIANT

    # Retail evaluation -> NON_COMPLIANT (MRP is mandatory on retail)
    retail_result = rule_engine.evaluate(
        declarations=declarations_lacking_mrp,
        package_type="retail",
        overall_confidence=0.96,
    )
    # Notice that retail also has absent mandatory count (mrp, date, batch) >= 3 => NEEDS_REVIEW
    # either way it is not COMPLIANT
    assert retail_result.status in (ComplianceStatus.NON_COMPLIANT, ComplianceStatus.NEEDS_REVIEW)


def test_reconciliation_higher_confidence_replaces_lower(rule_engine):
    """Higher-confidence declaration replaces earlier lower-confidence declaration."""
    decls = [
        {
            "field_name": "manufacturer_name",
            "field_value": "Hershey India Pvt Ltd",
            "raw_text": "Hershey India Pvt Ltd",
            "confidence": 0.70,
            "image_id": "img-1",
            "panel": "FRONT",
        },
        {
            "field_name": "manufacturer_name",
            "field_value": "Hershey India Private Limited",
            "raw_text": "Manufactured by Hershey India Private Limited",
            "confidence": 0.95,
            "image_id": "img-2",
            "panel": "BACK",
        },
    ]
    reconciled = rule_engine.reconcile_declarations(decls)
    assert reconciled["manufacturer_name"]["confidence"] == 0.95
    assert reconciled["manufacturer_name"]["field_value"] == "Hershey India Private Limited"
    assert reconciled["manufacturer_name"]["image_id"] == "img-2"
    assert reconciled["manufacturer_name"]["panel"] == "BACK"


def test_reconciliation_lower_confidence_does_not_replace_higher(rule_engine):
    """Lower-confidence declaration must NOT replace earlier higher-confidence declaration."""
    decls = [
        {
            "field_name": "mrp",
            "field_value": "65.00",
            "raw_text": "MRP Rs 65.00",
            "confidence": 0.98,
            "image_id": "img-1",
            "panel": "BACK",
        },
        {
            "field_name": "mrp",
            "field_value": "65",
            "raw_text": "65",
            "confidence": 0.50,
            "image_id": "img-2",
            "panel": "FRONT",
        },
    ]
    reconciled = rule_engine.reconcile_declarations(decls)
    assert reconciled["mrp"]["confidence"] == 0.98
    assert reconciled["mrp"]["field_value"] == "65.00"
    assert reconciled["mrp"]["image_id"] == "img-1"
    assert reconciled["mrp"]["panel"] == "BACK"


def test_reconciliation_null_empty_does_not_replace_present(rule_engine):
    """Null, empty, or 0.0-confidence declaration must NEVER replace a present declaration."""
    decls = [
        {
            "field_name": "country_of_origin",
            "field_value": "India",
            "raw_text": "Country of Origin: India",
            "confidence": 0.92,
            "image_id": "img-1",
            "panel": "BACK",
        },
        {
            "field_name": "country_of_origin",
            "field_value": None,
            "raw_text": None,
            "confidence": 0.0,
            "image_id": "img-2",
            "panel": "FRONT",
        },
        {
            "field_name": "country_of_origin",
            "field_value": "",
            "raw_text": "",
            "confidence": 0.85,
            "image_id": "img-3",
            "panel": "SIDE",
        },
    ]
    reconciled = rule_engine.reconcile_declarations(decls)
    assert reconciled["country_of_origin"]["field_value"] == "India"
    assert reconciled["country_of_origin"]["confidence"] == 0.92
    assert reconciled["country_of_origin"]["image_id"] == "img-1"
    assert reconciled["country_of_origin"]["panel"] == "BACK"


def test_reconciliation_equal_confidence_tie_break_deterministic(rule_engine):
    """
    Equal-confidence tie break:
    1. Prefer longer/more descriptive raw_text or field_value.
    2. If lengths are equal: first-observed wins (deterministic).
    """
    # Case 1: Same confidence, one is more descriptive
    decls_descriptive = [
        {
            "field_name": "manufacturer_address",
            "field_value": "Mumbai 400001",
            "raw_text": "Mumbai 400001",
            "confidence": 0.90,
            "image_id": "img-1",
        },
        {
            "field_name": "manufacturer_address",
            "field_value": "Plot 10, MIDC Industrial Area, Andheri East, Mumbai 400001",
            "raw_text": "Plot 10, MIDC Industrial Area, Andheri East, Mumbai 400001",
            "confidence": 0.90,
            "image_id": "img-2",
        },
    ]
    reconciled1 = rule_engine.reconcile_declarations(decls_descriptive)
    assert reconciled1["manufacturer_address"]["image_id"] == "img-2"
    assert "MIDC" in reconciled1["manufacturer_address"]["field_value"]

    # Case 2: Same confidence, identical text length: first observed wins
    decls_identical_length = [
        {
            "field_name": "net_quantity",
            "field_value": "40 g",
            "raw_text": "40 g",
            "confidence": 0.95,
            "image_id": "img-first",
        },
        {
            "field_name": "net_quantity",
            "field_value": "50 g",
            "raw_text": "50 g",
            "confidence": 0.95,
            "image_id": "img-second",
        },
    ]
    reconciled2 = rule_engine.reconcile_declarations(decls_identical_length)
    assert reconciled2["net_quantity"]["image_id"] == "img-first"
    assert reconciled2["net_quantity"]["field_value"] == "40 g"


def test_reconciliation_multi_panel_3_images(rule_engine):
    """Multi-panel inspection with 3 images correctly reconciles all fields."""
    image1_front = [
        {"field_name": "commodity_name", "field_value": "Milk Chocolate Bar", "confidence": 0.96, "image_id": "img-front", "panel": "FRONT"},
        {"field_name": "net_quantity", "field_value": "40 g", "confidence": 0.94, "image_id": "img-front", "panel": "FRONT"},
        {"field_name": "mrp", "field_value": None, "confidence": 0.0, "image_id": "img-front", "panel": "FRONT"},
    ]
    image2_back = [
        {"field_name": "mrp", "field_value": "65.00", "confidence": 0.98, "image_id": "img-back", "panel": "BACK"},
        {"field_name": "manufacturer_name", "field_value": "Hershey India Pvt Ltd", "confidence": 0.92, "image_id": "img-back", "panel": "BACK"},
        {"field_name": "manufacturer_address", "field_value": "Plot 1, MIDC Mandideep 462046", "confidence": 0.90, "image_id": "img-back", "panel": "BACK"},
        {"field_name": "manufacturing_date", "field_value": "2024-05", "confidence": 0.93, "image_id": "img-back", "panel": "BACK"},
        {"field_name": "batch_number", "field_value": "B-4019", "confidence": 0.89, "image_id": "img-back", "panel": "BACK"},
        {"field_name": "net_quantity", "field_value": "40g", "confidence": 0.85, "image_id": "img-back", "panel": "BACK"},
    ]
    image3_side = [
        {"field_name": "consumer_care_info", "field_value": "care@hershey.com", "confidence": 0.91, "image_id": "img-side", "panel": "SIDE"},
        {"field_name": "country_of_origin", "field_value": "India", "confidence": 0.95, "image_id": "img-side", "panel": "SIDE"},
        {"field_name": "unit_sale_price", "field_value": "Rs 1.625 / g", "confidence": 0.88, "image_id": "img-side", "panel": "SIDE"},
        {"field_name": "mrp", "field_value": "65", "confidence": 0.70, "image_id": "img-side", "panel": "SIDE"},
    ]

    all_decls = image1_front + image2_back + image3_side
    reconciled = rule_engine.reconcile_declarations(all_decls)

    # FRONT wins net_quantity (0.94 > 0.85)
    assert reconciled["net_quantity"]["image_id"] == "img-front"
    # BACK wins mrp (0.98 > 0.70 > 0.0)
    assert reconciled["mrp"]["image_id"] == "img-back"
    assert reconciled["mrp"]["field_value"] == "65.00"
    # SIDE wins consumer_care_info & country_of_origin
    assert reconciled["consumer_care_info"]["image_id"] == "img-side"
    assert reconciled["country_of_origin"]["image_id"] == "img-side"


def test_decoupled_confidence_metric_and_coverage(rule_engine):
    """Mean confidence must only average extracted fields, and coverage must be tracked separately."""
    decls = [
        {"field_name": "mrp", "field_value": "65.00", "confidence": 0.95},
        {"field_name": "net_quantity", "field_value": "40 g", "confidence": 0.90},
        {"field_name": "unit_sale_price", "field_value": "Rs 1.625 / g", "confidence": 0.94},
        # 8 mandatory fields absent
        {"field_name": "commodity_name", "field_value": None, "confidence": 0.0},
        {"field_name": "manufacturer_name", "field_value": None, "confidence": 0.0},
        {"field_name": "manufacturer_address", "field_value": None, "confidence": 0.0},
        {"field_name": "manufacturing_date", "field_value": None, "confidence": 0.0},
        {"field_name": "batch_number", "field_value": None, "confidence": 0.0},
        {"field_name": "consumer_care_info", "field_value": None, "confidence": 0.0},
        {"field_name": "country_of_origin", "field_value": None, "confidence": 0.0},
    ]

    result = rule_engine.evaluate(declarations=decls, package_type="retail")

    # Mean confidence should be ~0.93 ((0.95 + 0.90 + 0.94) / 3 = 0.93), NOT 0.25!
    assert 0.92 <= result.confidence_score <= 0.94
    assert result.fields_extracted == 2  # commodity_name, manufacturer_name etc. absent; mrp and net_quantity present
    assert result.status == ComplianceStatus.NEEDS_REVIEW
    # Verify reason mentions incomplete inspection, not low AI confidence
    assert any("Incomplete inspection" in note for note in result.notes)
    assert not any("Low extraction confidence" in note for note in result.notes)


def test_conditional_check_missing_context_triggers_needs_review(rule_engine):
    """If a conditional rule's context key is omitted, it must return NEEDS_REVIEW, not NOT_APPLICABLE."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "DATE-002")
    decl = {"field_name": "best_before_date", "field_value": None}
    # Empty product_context (is_perishable missing)
    res = rule_engine._check_conditional(rule, decl, product_context={})
    assert res.status == RuleEvaluationStatus.NEEDS_REVIEW
    assert "not provided" in res.reason


def test_conditional_check_inactive_condition_returns_not_applicable(rule_engine):
    """If a conditional rule's context key is explicitly False, it returns NOT_APPLICABLE."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "DATE-002")
    decl = {"field_name": "best_before_date", "field_value": None}
    res = rule_engine._check_conditional(rule, decl, product_context={"is_perishable": False})
    assert res.status == RuleEvaluationStatus.NOT_APPLICABLE
    assert res.violation is None


def test_conditional_check_active_missing_decl_fails(rule_engine):
    """If a conditional rule's context key is True and field is missing, it returns FAILED with a violation."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "DATE-002")
    decl = {"field_name": "best_before_date", "field_value": None}
    res = rule_engine._check_conditional(rule, decl, product_context={"is_perishable": True})
    assert res.status == RuleEvaluationStatus.FAILED
    assert res.violation is not None
    assert res.violation.rule_id == "DATE-002"


def test_citation_verified_field_on_violations(rule_engine):
    """Every rule violation must carry citation_verified: bool matching the rule definition."""
    rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "MRP-001")
    res = rule_engine._check_presence(rule, None)
    assert res.status == RuleEvaluationStatus.FAILED
    assert hasattr(res.violation, "citation_verified")
    assert isinstance(res.violation.citation_verified, bool)
    assert res.violation.citation_verified is False


def test_cross_field_arithmetic_consistency_warning(rule_engine):
    """MRP ÷ Net Quantity mismatching USP by > 15% must emit a data integrity warning."""
    # e.g. 5 kg at ₹90/kg should be ₹450, but MRP is ₹65 (the mixed Hershey/Rice fixture)
    decls = [
        {"field_name": "commodity_name", "field_value": "Rice", "confidence": 0.95},
        {"field_name": "net_quantity", "field_value": "5 kg", "confidence": 0.95},
        {"field_name": "mrp", "field_value": "₹ 65.00", "confidence": 0.95},
        {"field_name": "unit_sale_price", "field_value": "Rs. 90.00 / kg", "confidence": 0.95},
    ]
    res = rule_engine.evaluate(declarations=decls, package_type="retail")
    assert any("Data integrity warning: MRP" in note and "does not approximate declared Unit Sale Price" in note for note in res.notes)


def test_cross_panel_commodity_name_disagreement_warning(rule_engine):
    """Conflicting commodity names across panels must emit a cross-panel data integrity warning."""
    decls = [
        {"field_name": "commodity_name", "field_value": "HEY'S", "panel": "FRONT", "confidence": 0.90},
        {"field_name": "commodity_name", "field_value": "Premium Basmati Rice", "panel": "BACK", "confidence": 0.95},
    ]
    res = rule_engine.evaluate(declarations=decls, package_type="retail")
    assert any("Discrepancy between commodity names on different panels" in note for note in res.notes)



