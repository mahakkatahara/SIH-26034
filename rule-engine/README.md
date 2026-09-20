# Rule Engine — Legal Metrology Inspection System

## Overview

The rule engine is the **deterministic compliance decision-maker**.

> **Design Principle:** The AI/LLM is NEVER the legal decision-maker.
> 
> The AI pipeline extracts structured declarations and text bounding boxes from package images.
> The deterministic rule engine (`rule-engine/engine.py`) strictly evaluates that data against statutory rules.
> Every compliance finding carries: `rule_id`, `field`, `observed_value`, `expected`, `severity`, `legal_reference`, and confidence.
> LLM/RAG (Phase 7) is reserved solely for natural language explanations and statutory referencing.

---

## Architecture

```
PipelineResult (from AI module)
    │  Structured declarations:
    │  [{field_name: "mrp", field_value: "50.0", raw_text: "MRP Rs. 50.00", confidence: 0.95}, ...]
    ▼
RuleEngine.evaluate(declarations, product_category, package_type, ...)
    │
    ├── Filter applicable rules from rules/rules.json by category and package_type (retail vs wholesale)
    ├── For each applicable rule:
    │    ├── presence_check: Is the mandatory declaration present and non-empty?
    │    ├── format_check: Does the value/raw text conform to the statutory regex pattern?
    │    ├── unit_check: Is the measurement unit valid per Legal Metrology schedules (normalized)?
    │    ├── conditional_check: Is the rule triggered by product context (e.g., imported commodity)?
    │    ├── pdp_placement: Are mandatory declarations correctly grouped on the PDP?
    │    └── font_size_check: Does declaration meet minimum numeral height (FONT-001)?
    │
    ├── Statutory Safeguards:
    │    ├── Confidence safeguard: If mean AI confidence < AI_CONFIDENCE_THRESHOLD (0.75) → NEEDS_REVIEW
    │    └── Single-panel safeguard: If >= 3 mandatory fields missing → NEEDS_REVIEW (unseen panel suspected)
    │
    └── ComplianceResult
         ├── status: COMPLIANT | NON_COMPLIANT | WARNING | NEEDS_REVIEW
         ├── violations: [RuleViolation, ...] (HIGH severity statutory non-compliances)
         ├── warnings: [RuleViolation, ...] (MEDIUM/LOW severity warnings)
         └── confidence_score: float
```

---

## Implementation Status

| Phase | Feature | Status | Details |
|-------|---------|--------|---------|
| Phase 1 | Rule schema and JSON loading | ✅ **Complete** | Pydantic / dataclass loading, caching, version tracking |
| Phase 4 | `presence_check` | ✅ **Complete** | Mandatory presence verification per Rule 6(1) |
| Phase 4 | `format_check` | ✅ **Complete** | Regex validation for MRP syntax, dates, consumer care info |
| Phase 4 | `unit_check` | ✅ **Complete** | Canonical unit normalization (`UNIT_NORMALIZATION_MAP`) |
| Phase 4 | `conditional_check` | ✅ **Complete** | Evaluates context flags (e.g. `is_imported` under Rule 6(1)(k)) |
| Phase 4 | Wholesale scoping (Rule 24) | ✅ **Complete** | Exempts wholesale packages from retail-specific declarations |
| Phase 4 | Single-panel threshold protection | ✅ **Complete** | Missing $\ge 3$ declarations triggers `NEEDS_REVIEW` |
| Phase 5 | Visual evidence linking | ✅ **Complete** | Violations mapped to declaration UUIDs and bounding boxes |
| Phase 6 | `font_size_check` | 🟡 **Partial** | `FONT-001` implemented; physical mm calibration against DPI pending |

---

## Rule Schema

Each rule in `rules/rules.json` adheres to the following specification:

```json
{
  "rule_id": "MRP-001",
  "field": "mrp",
  "category": null,
  "package_type": "retail",
  "mandatory": true,
  "severity": "HIGH",
  "description": "MRP must be declared on every pre-packaged commodity inclusive of all taxes",
  "validation_logic": {
    "type": "presence_check",
    "field": "mrp"
  },
  "legal_reference": "Rule 6(1)(f) — Legal Metrology (Packaged Commodities) Rules, 2011",
  "citation_verified": false,
  "rule_version": "1.0"
}
```

### Statutory Citation Verification
Every rule must include a `citation_verified` boolean field (defaults to `false`). In accordance with project governance, this must never be marked `true` without formal legal verification against the official Gazette of India.

---

## Statutory Safeguards Against False Non-Compliance

1. **Unphotographed Panel Safeguard:**
   Package inspections frequently provide an image of only one side of a carton. If 3 or more mandatory declarations are absent, the engine downgrades the outcome to `NEEDS_REVIEW` rather than flagging `NON_COMPLIANT`, ensuring officers physically inspect remaining panels.
2. **Confidence Threshold:**
   If `overall_confidence < AI_CONFIDENCE_THRESHOLD` (default: 0.75), the status is downgraded to `NEEDS_REVIEW` with the prompt:
   > *"Human verification recommended."*

---

## Compliance Status Values

| Status | Statutory Definition |
|--------|---------------------|
| `COMPLIANT` | All mandatory statutory rules pass without violation |
| `NON_COMPLIANT` | One or more `HIGH` severity rules fail (clear statutory contravention) |
| `WARNING` | Minor advisory infractions (`MEDIUM` or `LOW` severity) |
| `NEEDS_REVIEW` | Low AI extraction confidence, unphotographed panel suspected, or stub mode |
| `PENDING` | Analysis not yet initiated |

---

## Adding New Rules

1. Add the new rule definition to `rules/rules.json`.
2. Ensure `package_type` is specified (`"retail"`, `"wholesale"`, or `"any"`).
3. Set `citation_verified: false` by default.
4. If introducing a new `validation_logic.type`, implement the handler method in `engine.py`.
5. Run the test suite: `pytest backend/tests/test_rule_engine.py` to prove functionality.
