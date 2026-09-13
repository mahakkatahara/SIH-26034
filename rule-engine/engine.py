"""
Rule Engine — Deterministic Compliance Evaluator
=======================================================
⚠ PHASE 1 STUB: Full rule evaluation logic will be implemented in Phase 4.

This module provides the interface and skeleton for the rule engine.
The rule engine is DETERMINISTIC — it does NOT use AI/LLM for decisions.

Pipeline position:
    PipelineResult (from AI module)
        ↓
    RuleEngine.evaluate()
        ↓
    ComplianceResult (COMPLIANT | NON_COMPLIANT | WARNING | NEEDS_REVIEW)
"""
import json
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


class ComplianceStatus(str, Enum):
    COMPLIANT = "COMPLIANT"
    NON_COMPLIANT = "NON_COMPLIANT"
    WARNING = "WARNING"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    PENDING = "PENDING"


class ViolationSeverity(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class RuleDefinition:
    """A compliance rule loaded from rules.json."""
    rule_id: str
    field: str
    mandatory: bool
    severity: ViolationSeverity
    description: str
    validation_logic: Dict[str, Any]
    legal_reference: Optional[str] = None
    category: Optional[str] = None
    rule_version: str = "1.0"


@dataclass
class RuleViolation:
    """A violation detected by the rule engine."""
    rule_id: str
    field: str
    severity: ViolationSeverity
    description: str
    legal_reference: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class ComplianceResult:
    """
    The overall compliance result for one inspection/image.
    Output of the rule engine.
    """
    status: ComplianceStatus
    violations: List[RuleViolation] = field(default_factory=list)
    warnings: List[RuleViolation] = field(default_factory=list)
    evaluated_rules: int = 0
    confidence_score: float = 0.0
    is_stub: bool = False
    stub_notice: Optional[str] = None


class RuleEngine:
    """
    Deterministic rule-based compliance checker.

    The engine loads rules from rules.json and evaluates
    extracted declarations against each applicable rule.

    ⚠ Phase 1: evaluate() returns a NEEDS_REVIEW stub result.
    Phase 4 will implement actual validation_logic evaluation.
    """

    STUB_NOTICE = (
        "⚠ RULE ENGINE NOT FULLY IMPLEMENTED (Phase 1 — Stub). "
        "Full deterministic validation will be integrated in Phase 4. "
        "All results currently require HUMAN REVIEW."
    )

    def __init__(self, rules_path: Optional[str] = None):
        """
        Initialize the rule engine.

        Args:
            rules_path: Path to rules.json file. If None, uses default location.
        """
        if rules_path is None:
            rules_path = os.path.join(os.path.dirname(__file__), "rules", "rules.json")

        self.rules: List[RuleDefinition] = self._load_rules(rules_path)
        self._rules_by_field: Dict[str, List[RuleDefinition]] = {}
        for rule in self.rules:
            self._rules_by_field.setdefault(rule.field, []).append(rule)

    def _load_rules(self, rules_path: str) -> List[RuleDefinition]:
        """Load and parse rules from JSON file."""
        if not os.path.exists(rules_path):
            return []
        with open(rules_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [
            RuleDefinition(
                rule_id=r["rule_id"],
                field=r["field"],
                mandatory=r.get("mandatory", True),
                severity=ViolationSeverity(r.get("severity", "HIGH")),
                description=r["description"],
                validation_logic=r.get("validation_logic", {}),
                legal_reference=r.get("legal_reference"),
                category=r.get("category"),
                rule_version=r.get("rule_version", "1.0"),
            )
            for r in data
        ]

    def get_rules_for_category(self, category: Optional[str] = None) -> List[RuleDefinition]:
        """
        Return rules applicable to a given product category.
        Rules with category=None apply to all products.
        """
        return [
            r for r in self.rules
            if r.category is None or r.category == category
        ]

    def evaluate(
        self,
        declarations: List[Dict[str, Any]],
        product_category: Optional[str] = None,
    ) -> ComplianceResult:
        """
        Evaluate extracted declarations against applicable rules.

        ⚠ PHASE 1 STUB: Returns NEEDS_REVIEW without actual evaluation.

        Args:
            declarations: List of dicts with field_name, field_value, confidence_score.
            product_category: Product category for category-specific rules.

        Returns:
            ComplianceResult with violations, warnings, and overall status.
        """
        # ── Phase 1: Stub implementation ──────────────────────────────────
        # TODO Phase 4: Implement actual rule validation logic
        # Each rule's validation_logic dict describes how to evaluate:
        #   - "presence_check": field exists and is non-empty
        #   - "format_check": value matches regex pattern
        #   - "unit_check": unit is in allowed list
        #   - "font_size_check": font height meets minimum
        #   - "visibility_check": text region is not obscured
        #   - "conditional_check": evaluate only if condition is met

        return ComplianceResult(
            status=ComplianceStatus.NEEDS_REVIEW,
            violations=[],
            warnings=[],
            evaluated_rules=len(self.get_rules_for_category(product_category)),
            confidence_score=0.0,
            is_stub=True,
            stub_notice=self.STUB_NOTICE,
        )

    def get_all_rules(self) -> List[RuleDefinition]:
        """Return all loaded rules."""
        return self.rules

    def get_rule_count(self) -> int:
        """Return the total number of loaded rules."""
        return len(self.rules)


# Module-level singleton (loaded once)
_engine_instance: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Get or create the module-level rule engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RuleEngine()
    return _engine_instance
