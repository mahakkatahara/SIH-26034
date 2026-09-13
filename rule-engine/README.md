# Rule Engine — Legal Metrology Inspection System

## Overview

The rule engine is the **deterministic compliance decision-maker**.

> **Design Principle:** The LLM/AI is NOT the legal decision-maker.
> 
> The AI pipeline extracts structured data from images.
> The rule engine applies deterministic rules to that data.
> LLM/RAG (Phase 7) provides natural-language explanation only.

## Architecture

```
PipelineResult (from AI module)
    │  Structured declarations:
    │  [{field_name: "mrp", field_value: "Rs. 50", confidence: 0.92}, ...]
    ▼
RuleEngine.evaluate(declarations, product_category)
    │
    ├── Load applicable rules from rules.json
    ├── For each rule:
    │    ├── presence_check: Is the field present and non-empty?
    │    ├── format_check: Does the value match the required pattern?
    │    ├── unit_check: Is the unit in the allowed list?
    │    ├── font_size_check: Is the font large enough?
    │    └── conditional_check: Evaluate only if condition is met
    │
    └── ComplianceResult
         ├── status: COMPLIANT | NON_COMPLIANT | WARNING | NEEDS_REVIEW
         ├── violations: [RuleViolation, ...]
         └── confidence_score: float
```

## Implementation Status

| Phase | Feature | Status |
|-------|---------|--------|
| Phase 1 | Rule schema and JSON loading | ✅ Done |
| Phase 1 | Rule engine stub (NEEDS_REVIEW for all) | ✅ Done |
| Phase 4 | `presence_check` implementation | 🔲 Planned |
| Phase 4 | `format_check` implementation | 🔲 Planned |
| Phase 4 | `unit_check` implementation | 🔲 Planned |
| Phase 6 | `font_size_check` implementation | 🔲 Planned |

## Rule Schema

Each rule in `rules/rules.json`:

```json
{
  "rule_id": "MRP-001",
  "field": "mrp",
  "category": null,
  "mandatory": true,
  "severity": "HIGH",
  "description": "MRP must be declared on every pre-packaged commodity",
  "validation_logic": {
    "type": "presence_check",
    "field": "mrp"
  },
  "legal_reference": "Rule 6(1)(f) — Legal Metrology (PC) Rules, 2011",
  "rule_version": "1.0"
}
```

## Compliance Status Values

| Status | Meaning |
|--------|---------|
| `COMPLIANT` | All mandatory rules pass |
| `NON_COMPLIANT` | One or more HIGH severity rules fail |
| `WARNING` | Only MEDIUM/LOW severity issues found |
| `NEEDS_REVIEW` | Confidence below threshold or stub mode |
| `PENDING` | Analysis not yet started |

## Confidence Threshold

If `ai_confidence_score < AI_CONFIDENCE_THRESHOLD` (default: 0.75),
the result is downgraded to `NEEDS_REVIEW` and the UI shows:
> "Human verification recommended."

## Adding New Rules

1. Add rule to `rules/rules.json` following the schema above
2. Set `rule_version` to the next semantic version
3. Implement the `validation_logic.type` handler in `engine.py` if needed
4. Reload the engine (or restart the service)

Rules are loaded at startup and cached. No code changes needed for new rules.
