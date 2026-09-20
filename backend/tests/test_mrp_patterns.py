"""
Unit tests for MRP-002 regex pattern matching real-world Indian label variations.

Verifies:
- Direct regex compilation and matching against >= 12 real-world price declaration formats:
  - Header variants: "M.R.P.", "Maximum Retail Price", "MRP:"
  - Currency variants: "Rs.", "Rs", "₹", "INR"
  - Numeric formats: integers, decimals, comma separators (Indian numbering: 1,00,000), suffix "/-"
  - Combined strings with tax annotations
- Negative cases: non-price package declarations must NOT match.
- RuleEngine format_check integration test using MRP-002 rule definition.
"""
import re
import pytest
from engine import RuleEngine, RuleEvaluationStatus


# Pattern defined in rules.json for MRP-002
MRP_PATTERN = (
    r"(?:(?:M\.?R\.?P\.?|Maximum\s+Retail\s+Price)\s*:?\s*(?:(?:Rs\.?|₹|INR)\s*)?"
    r"(?:[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?\s*(?:/-)?)?|"
    r"(?:Rs\.?|₹|INR)\s*[0-9]{1,3}(?:,[0-9]{2,3})*(?:\.[0-9]{1,2})?\s*(?:/-)?)"
)


MATCHING_MRP_STRINGS = [
    "M.R.P.",
    "Maximum Retail Price",
    "MRP:",
    "MRP ₹ 50/-",
    "₹50.00",
    "Rs. 50/-",
    "M.R.P. Rs. 2,450.50",
    "Maximum Retail Price: ₹ 1,499.00/-",
    "MRP: Rs. 99.00",
    "₹ 1,00,000/-",
    "Rs 500/-",
    "MRP Rs. 450.00 (inclusive of all taxes)",
    "INR 250.00",
    "MRP 150.00",
    "M.R.P.: ₹ 45.00",
]


NON_MATCHING_STRINGS = [
    "Manufactured by Pure Agro Foods Private Limited",
    "Net Quantity: 500 g",
    "Best before 6 months from packaging",
    "Customer care: 1800-111-222, email: help@example.com",
    "Batch No. B-98765",
    "Store in a cool and dry place away from direct sunlight",
]


@pytest.fixture
def rule_engine():
    """Initializes the rule engine with default rules.json."""
    return RuleEngine()


@pytest.mark.parametrize("mrp_text", MATCHING_MRP_STRINGS)
def test_mrp_regex_positive_matches(mrp_text):
    """Direct regex check: asserts all valid real-world MRP patterns match."""
    match = re.search(MRP_PATTERN, mrp_text, re.IGNORECASE)
    assert match is not None, f"Failed to match valid MRP text: {mrp_text}"


@pytest.mark.parametrize("non_mrp_text", NON_MATCHING_STRINGS)
def test_mrp_regex_negative_matches(non_mrp_text):
    """Direct regex check: asserts non-price strings do NOT match."""
    match = re.search(MRP_PATTERN, non_mrp_text, re.IGNORECASE)
    assert match is None, f"Incorrectly matched non-MRP text: {non_mrp_text}"


@pytest.mark.parametrize("mrp_text", MATCHING_MRP_STRINGS)
def test_rule_engine_mrp_002_passes_on_valid_formats(rule_engine, mrp_text):
    """RuleEngine integration: verifies MRP-002 format_check passes on real-world formats."""
    mrp_rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "MRP-002")
    decl = {
        "declaration_id": "decl-mrp",
        "field_name": "mrp",
        "field_value": mrp_text,
        "raw_text": mrp_text,
        "confidence": 0.98,
    }
    result = rule_engine._check_format(mrp_rule, decl)
    assert result.status == RuleEvaluationStatus.PASSED, f"MRP-002 failed on: {mrp_text}"
    assert result.violation is None


@pytest.mark.parametrize("non_mrp_text", NON_MATCHING_STRINGS)
def test_rule_engine_mrp_002_fails_on_invalid_formats(rule_engine, non_mrp_text):
    """RuleEngine integration: verifies MRP-002 format_check fails on non-MRP text."""
    mrp_rule = next(r for r in rule_engine.get_all_rules() if r.rule_id == "MRP-002")
    decl = {
        "declaration_id": "decl-mrp",
        "field_name": "mrp",
        "field_value": non_mrp_text,
        "raw_text": non_mrp_text,
        "confidence": 0.98,
    }
    result = rule_engine._check_format(mrp_rule, decl)
    assert result.status == RuleEvaluationStatus.FAILED, f"MRP-002 should have failed on: {non_mrp_text}"
    assert result.violation is not None
    assert result.violation.rule_id == "MRP-002"
