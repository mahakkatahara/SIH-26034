"""
Rule Engine — Deterministic Compliance Evaluator
=======================================================
The rule engine is the DETERMINISTIC compliance decision-maker.
In accordance with system architecture and AGENTS.md:
- An LLM must NEVER decide COMPLIANT or NON_COMPLIANT.
- The AI/vision pipeline extracts text and bounding boxes; RuleEngine decides.
- Every compliance finding carries: rule_id, field, observed_value, expected,
  severity, legal_reference, and declaration_id.
- If overall confidence < AI_CONFIDENCE_THRESHOLD, or if >= 3 mandatory fields
  are absent, downgrade to NEEDS_REVIEW (unphotographed panel suspected).
- Note: Gemini vision model currently self-reports confidence ~0.99 for nearly
  every field (not yet calibrated). The missing-mandatory-field count is the
  primary protection against false non-compliance.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any, Union


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


class RuleEvaluationStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# ─── Canonical unit normalization mapping ──────────────────────────────────────
# Normalizes common packaging abbreviations and variants to standard SI/legal forms
UNIT_NORMALIZATION_MAP: Dict[str, str] = {
    # Mass
    "gm": "g",
    "gram": "g",
    "grams": "g",
    "g": "g",
    "kg": "kg",
    "kgs": "kg",
    "kilogram": "kg",
    "kilograms": "kg",
    # Volume
    "ml": "ml",
    "millilitre": "ml",
    "milliliter": "ml",
    "millilitres": "ml",
    "milliliters": "ml",
    "l": "l",
    "ltr": "l",
    "litre": "l",
    "liter": "l",
    "litres": "l",
    "liters": "l",
    # Length
    "cm": "cm",
    "centimetre": "cm",
    "centimeter": "cm",
    "m": "m",
    "metre": "m",
    "meter": "m",
    # Count / units
    "nos": "nos",
    "pcs": "nos",
    "pc": "nos",
    "piece": "nos",
    "pieces": "nos",
    "number": "nos",
    "units": "nos",
    "unit": "nos",
}


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
    citation_verified: bool = False
    category: Optional[str] = None
    rule_version: str = "1.0"


@dataclass
class RuleViolation:
    """A violation or warning detected by the rule engine."""
    rule_id: str
    field: str
    severity: ViolationSeverity
    description: str
    observed_value: Optional[Any] = None
    expected: Optional[str] = None
    legal_reference: Optional[str] = None
    declaration_id: Optional[str] = None
    evidence: Optional[Dict[str, Any]] = None


@dataclass
class RuleEvaluationResult:
    """Outcome of evaluating a single rule."""
    rule_id: str
    field: str
    status: RuleEvaluationStatus
    violation: Optional[RuleViolation] = None
    reason: Optional[str] = None


@dataclass
class ComplianceResult:
    """
    The overall compliance result for one inspection.
    Output of the deterministic rule engine.
    """
    status: ComplianceStatus
    violations: List[RuleViolation] = field(default_factory=list)
    warnings: List[RuleViolation] = field(default_factory=list)
    rule_results: List[RuleEvaluationResult] = field(default_factory=list)
    evaluated_rules: int = 0
    confidence_score: float = 0.0
    is_stub: bool = False
    stub_notice: Optional[str] = None
    notes: List[str] = field(default_factory=list)


class RuleEngine:
    """
    Deterministic rule-based compliance engine.

    Evaluates extracted declarations against Legal Metrology rules
    without any LLM intervention in legal decision-making.
    """

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
                citation_verified=r.get("citation_verified", False),
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

    def get_all_rules(self) -> List[RuleDefinition]:
        """Return all loaded rules."""
        return self.rules

    def get_rule_count(self) -> int:
        """Return the total number of loaded rules."""
        return len(self.rules)

    # ─── Declaration Normalization Helpers ─────────────────────────────────────

    @staticmethod
    def _normalize_declaration(decl: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
        """Converts dict or ORM/Pydantic object into a standardized dictionary."""
        if isinstance(decl, dict):
            field_name = decl.get("field_name")
            field_value = decl.get("field_value")
            raw_text = decl.get("raw_text")
            confidence = decl.get("confidence")
            if confidence is None:
                confidence = decl.get("confidence_score", 1.0)
            decl_id = decl.get("declaration_id") or decl.get("id")
            is_obscured = decl.get("is_obscured", False)
            bounding_box = decl.get("bounding_box")
            unit = decl.get("unit")
            normalized = decl.get("normalized")
        else:
            field_name = getattr(decl, "field_name", None)
            field_value = getattr(decl, "field_value", None)
            raw_text = getattr(decl, "raw_text", None)
            confidence = getattr(decl, "confidence", None)
            if confidence is None:
                confidence = getattr(decl, "confidence_score", 1.0)
            decl_id = getattr(decl, "declaration_id", None) or getattr(decl, "id", None)
            is_obscured = getattr(decl, "is_obscured", False)
            bounding_box = getattr(decl, "bounding_box", None)
            unit = getattr(decl, "unit", None)
            normalized = getattr(decl, "normalized", None)

        return {
            "field_name": field_name,
            "field_value": field_value,
            "raw_text": raw_text,
            "confidence": float(confidence) if confidence is not None else 0.0,
            "declaration_id": str(decl_id) if decl_id else None,
            "is_obscured": bool(is_obscured),
            "bounding_box": bounding_box,
            "unit": unit,
            "normalized": normalized,
        }

    @staticmethod
    def _is_present(decl: Optional[Dict[str, Any]]) -> bool:
        """True if field exists, is non-null, and stripped string length > 0."""
        if not decl:
            return False
        val = decl.get("field_value")
        if val is None:
            return False
        return len(str(val).strip()) > 0

    # ─── Individual Validation Logic Handlers ──────────────────────────────────

    def _check_presence(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        """
        presence_check: Field exists, value non-null, stripped length > 0.
        """
        if self._is_present(decl):
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.PASSED,
            )

        observed_val = decl.get("field_value") if decl else None
        decl_id = decl.get("declaration_id") if decl else None
        violation = RuleViolation(
            rule_id=rule.rule_id,
            field=rule.field,
            severity=rule.severity,
            description=f"Mandatory declaration '{rule.field}' is missing or empty on the package",
            observed_value=observed_val,
            expected="Present and non-empty declaration",
            legal_reference=rule.legal_reference,
            declaration_id=decl_id,
        )
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.FAILED,
            violation=violation,
            reason="Field is missing or empty",
        )

    def _check_format(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        """
        format_check: Regex from rule.pattern, honouring case_insensitive.
        Checks against raw_text or field_value.
        """
        pattern = rule.validation_logic.get("pattern", "")
        case_insensitive = rule.validation_logic.get("case_insensitive", False)
        flags = re.IGNORECASE if case_insensitive else 0

        if not decl or not self._is_present(decl):
            decl_id = decl.get("declaration_id") if decl else None
            violation = RuleViolation(
                rule_id=rule.rule_id,
                field=rule.field,
                severity=rule.severity,
                description=f"Cannot verify format: declaration '{rule.field}' is absent",
                observed_value=None,
                expected=f"Pattern: {pattern}",
                legal_reference=rule.legal_reference,
                declaration_id=decl_id,
            )
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.FAILED,
                violation=violation,
                reason="Field absent for format verification",
            )

        raw_text = str(decl.get("raw_text") or "")
        field_value = str(decl.get("field_value") or "")
        decl_id = decl.get("declaration_id")

        if (raw_text and re.search(pattern, raw_text, flags)) or (field_value and re.search(pattern, field_value, flags)):
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.PASSED,
            )

        observed = raw_text if raw_text else field_value
        violation = RuleViolation(
            rule_id=rule.rule_id,
            field=rule.field,
            severity=rule.severity,
            description=rule.description or f"Declaration '{rule.field}' does not conform to required format",
            observed_value=observed,
            expected=f"Format matching regex: {pattern}",
            legal_reference=rule.legal_reference,
            declaration_id=decl_id,
        )
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.FAILED,
            violation=violation,
            reason=f"Value '{observed}' does not match pattern {pattern}",
        )

    def _check_unit(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        """
        unit_check: Parsed unit is in allowed_units, case-insensitive,
        after normalizing common variants (gm/g/gram -> g, ltr/litre/l -> l, etc.).
        """
        allowed_units = rule.validation_logic.get("allowed_units", [])
        decl_id = decl.get("declaration_id") if decl else None

        if not decl or not self._is_present(decl):
            violation = RuleViolation(
                rule_id=rule.rule_id,
                field=rule.field,
                severity=rule.severity,
                description=f"Cannot verify unit: declaration '{rule.field}' is absent",
                observed_value=None,
                expected=f"Allowed units: {sorted(list(set(allowed_units)))}",
                legal_reference=rule.legal_reference,
                declaration_id=decl_id,
            )
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.FAILED,
                violation=violation,
                reason="Field absent for unit check",
            )

        # 1. Look for pre-parsed unit in decl or normalized dict
        extracted_unit: Optional[str] = None
        if decl.get("unit"):
            extracted_unit = str(decl["unit"]).strip().lower()
        elif isinstance(decl.get("normalized"), dict) and "unit" in decl["normalized"]:
            extracted_unit = str(decl["normalized"]["unit"]).strip().lower()
        elif isinstance(decl.get("normalized"), dict) and isinstance(decl["normalized"].get("net_quantity"), dict):
            extracted_unit = str(decl["normalized"]["net_quantity"].get("unit", "")).strip().lower()

        # 2. Extract unit via regex from field_value or raw_text if not pre-parsed
        if not extracted_unit:
            text_to_parse = str(decl.get("field_value") or decl.get("raw_text") or "")
            # Match trailing word tokens, e.g. "500 g", "5 kg", "1 ltr", "100 ml", "10 nos"
            match = re.search(r"(?:^|\d|\s)([a-zA-Z]+)\s*\.?$", text_to_parse.strip())
            if match:
                extracted_unit = match.group(1).strip().lower()

        if not extracted_unit:
            violation = RuleViolation(
                rule_id=rule.rule_id,
                field=rule.field,
                severity=rule.severity,
                description=f"No unit of measurement could be parsed from '{rule.field}'",
                observed_value=decl.get("field_value"),
                expected=f"Standard legal unit from: {sorted(list(set(allowed_units)))}",
                legal_reference=rule.legal_reference,
                declaration_id=decl_id,
            )
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.FAILED,
                violation=violation,
                reason="Unit could not be parsed",
            )

        # Normalize extracted unit and allowed units to canonical forms
        canonical_observed = UNIT_NORMALIZATION_MAP.get(extracted_unit, extracted_unit)
        canonical_allowed = {UNIT_NORMALIZATION_MAP.get(u.lower(), u.lower()) for u in allowed_units}

        # Check raw unit in allowed OR canonical unit in canonical allowed
        if extracted_unit in [u.lower() for u in allowed_units] or canonical_observed in canonical_allowed:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.PASSED,
            )

        violation = RuleViolation(
            rule_id=rule.rule_id,
            field=rule.field,
            severity=rule.severity,
            description=f"Unit '{extracted_unit}' is not an authorized legal metrology measurement unit",
            observed_value=extracted_unit,
            expected=f"Allowed legal units: {sorted(list(set(allowed_units)))}",
            legal_reference=rule.legal_reference,
            declaration_id=decl_id,
        )
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.FAILED,
            violation=violation,
            reason=f"Unit '{extracted_unit}' is not in allowed legal units",
        )

    def _check_conditional(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
        product_context: Dict[str, Any],
    ) -> RuleEvaluationResult:
        """
        conditional_check: Evaluate only when rule.condition holds against
        the product context (e.g. is_imported, is_perishable); else return NOT_APPLICABLE.
        """
        condition_key = rule.validation_logic.get("condition")
        condition_holds = bool(product_context.get(condition_key, False)) if condition_key else True

        if not condition_holds:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.NOT_APPLICABLE,
                reason=f"Condition '{condition_key}' not active for this product",
            )

        # Condition holds: verify field presence
        if self._is_present(decl):
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.PASSED,
            )

        decl_id = decl.get("declaration_id") if decl else None
        violation = RuleViolation(
            rule_id=rule.rule_id,
            field=rule.field,
            severity=rule.severity,
            description=f"Declaration '{rule.field}' is required because condition '{condition_key}' is active",
            observed_value=decl.get("field_value") if decl else None,
            expected=f"Declaration mandatory when {condition_key}=True",
            legal_reference=rule.legal_reference,
            declaration_id=decl_id,
        )
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.FAILED,
            violation=violation,
            reason=f"Required declaration '{rule.field}' missing under condition '{condition_key}'",
        )

    def _check_visibility(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
        confidence_threshold: float,
    ) -> RuleEvaluationResult:
        """
        visibility_check: Use declaration's confidence and an is_obscured flag.
        Low confidence or obscured => NEEDS_REVIEW, NEVER NON_COMPLIANT.
        """
        if not decl:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.NEEDS_REVIEW,
                reason=f"Declaration '{rule.field}' absent or unreadable; visibility requires human review",
            )

        is_obscured = decl.get("is_obscured", False)
        conf = float(decl.get("confidence", 1.0))

        if is_obscured:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.NEEDS_REVIEW,
                reason=f"Declaration '{rule.field}' flagged as obscured or overprinted",
            )

        if conf < confidence_threshold:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                field=rule.field,
                status=RuleEvaluationStatus.NEEDS_REVIEW,
                reason=f"Declaration '{rule.field}' confidence ({conf:.2f}) < threshold ({confidence_threshold:.2f})",
            )

        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.PASSED,
        )

    def _check_font_size(
        self,
        rule: RuleDefinition,
        decl: Optional[Dict[str, Any]],
    ) -> RuleEvaluationResult:
        """
        font_size_check: Stub is acceptable ONLY in this sprint — return
        NOT_APPLICABLE with reason 'font analysis pending (Sprint 7)'.
        Marked clearly, no fake measurements.
        """
        return RuleEvaluationResult(
            rule_id=rule.rule_id,
            field=rule.field,
            status=RuleEvaluationStatus.NOT_APPLICABLE,
            reason="font analysis pending (Sprint 7)",
        )

    # ─── Aggregation & Evaluation Engine ──────────────────────────────────────

    def evaluate(
        self,
        declarations: List[Union[Dict[str, Any], Any]],
        product_category: Optional[str] = None,
        product_context: Optional[Dict[str, Any]] = None,
        overall_confidence: Optional[float] = None,
        confidence_threshold: float = 0.75,
    ) -> ComplianceResult:
        """
        Evaluate extracted declarations against applicable rules.

        Aggregation Rules:
        - Any failed mandatory HIGH rule => NON_COMPLIANT.
        - Only MEDIUM/LOW failures => WARNING.
        - All mandatory rules pass => COMPLIANT.
        - If overall confidence < AI_CONFIDENCE_THRESHOLD (0.75), OR if
          3 or more mandatory fields are absent, downgrade to NEEDS_REVIEW
          (absent fields may simply be on an unphotographed panel).
        - NOT_APPLICABLE outcomes never affect the overall status.

        Args:
            declarations: List of extracted declarations (dicts or model objects).
            product_category: Optional category for category-specific rule filtering.
            product_context: Dict with context flags (e.g. is_imported, is_perishable).
            overall_confidence: Overall extraction confidence score (0.0 to 1.0).
            confidence_threshold: Confidence gate for human review (default 0.75).

        Returns:
            ComplianceResult with status, violations, warnings, and per-rule results.
        """
        ctx = product_context or {}

        # 1. Map declarations by field name
        decls_by_field: Dict[str, Dict[str, Any]] = {}
        confidences: List[float] = []

        for d in declarations:
            norm = self._normalize_declaration(d)
            fn = norm.get("field_name")
            if fn:
                decls_by_field[fn] = norm
                if norm.get("confidence") is not None:
                    confidences.append(norm["confidence"])

        # Compute overall confidence if not explicitly passed
        if overall_confidence is None:
            overall_confidence = float(sum(confidences) / len(confidences)) if confidences else 1.0

        applicable_rules = self.get_rules_for_category(product_category)

        # 2. Identify absent mandatory fields
        # Look at all mandatory rules with type 'presence_check'
        mandatory_presence_rules = [
            r for r in applicable_rules
            if r.mandatory and r.validation_logic.get("type") == "presence_check"
        ]
        absent_mandatory_fields = [
            r.field for r in mandatory_presence_rules
            if not self._is_present(decls_by_field.get(r.field))
        ]
        absent_mandatory_count = len(set(absent_mandatory_fields))

        # 3. Evaluate each rule deterministically
        violations: List[RuleViolation] = []
        warnings: List[RuleViolation] = []
        rule_results: List[RuleEvaluationResult] = []
        needs_review_reasons: List[str] = []
        notes: List[str] = []

        for rule in applicable_rules:
            v_type = rule.validation_logic.get("type", "presence_check")
            decl = decls_by_field.get(rule.field)

            if v_type == "presence_check":
                eval_res = self._check_presence(rule, decl)
            elif v_type == "format_check":
                eval_res = self._check_format(rule, decl)
            elif v_type == "unit_check":
                eval_res = self._check_unit(rule, decl)
            elif v_type == "conditional_check":
                eval_res = self._check_conditional(rule, decl, ctx)
            elif v_type == "visibility_check":
                eval_res = self._check_visibility(rule, decl, confidence_threshold)
            elif v_type == "font_size_check":
                eval_res = self._check_font_size(rule, decl)
            else:
                eval_res = self._check_presence(rule, decl)

            rule_results.append(eval_res)

            if eval_res.status == RuleEvaluationStatus.FAILED and eval_res.violation:
                if rule.severity == ViolationSeverity.HIGH:
                    violations.append(eval_res.violation)
                else:
                    warnings.append(eval_res.violation)
            elif eval_res.status == RuleEvaluationStatus.NEEDS_REVIEW and eval_res.reason:
                needs_review_reasons.append(f"{rule.rule_id} ({rule.field}): {eval_res.reason}")

        # 4. Status Aggregation Logic
        # Note: Gemini vision model currently self-reports confidence ~0.99 for nearly all fields
        # (not yet calibrated). The missing-mandatory-field count is the primary protection
        # against false non-compliance from unphotographed package panels.

        status: ComplianceStatus

        if absent_mandatory_count >= 3:
            # 3 or more mandatory fields are absent: suspect unphotographed panel
            status = ComplianceStatus.NEEDS_REVIEW
            note = (
                f"{absent_mandatory_count} mandatory fields absent ({', '.join(sorted(set(absent_mandatory_fields)))}). "
                f"Downgraded to NEEDS_REVIEW as missing fields may reside on unphotographed package panels."
            )
            notes.append(note)
        elif overall_confidence < confidence_threshold:
            # Low overall AI confidence gate
            status = ComplianceStatus.NEEDS_REVIEW
            note = (
                f"Overall extraction confidence ({overall_confidence:.2f}) is below "
                f"verification threshold ({confidence_threshold:.2f}). Downgraded to NEEDS_REVIEW."
            )
            notes.append(note)
        elif any(r.mandatory and r.severity == ViolationSeverity.HIGH for r in applicable_rules if any(v.rule_id == r.rule_id for v in violations)):
            # Mandatory HIGH rule failure
            status = ComplianceStatus.NON_COMPLIANT
        elif warnings:
            # Only MEDIUM / LOW severity issues
            status = ComplianceStatus.WARNING
        elif needs_review_reasons:
            # All mandatory pass, but specific visibility/confidence review flagged
            status = ComplianceStatus.NEEDS_REVIEW
            notes.extend(needs_review_reasons)
        else:
            # All mandatory rules passed, no warnings, no reviews
            status = ComplianceStatus.COMPLIANT

        return ComplianceResult(
            status=status,
            violations=violations,
            warnings=warnings,
            rule_results=rule_results,
            evaluated_rules=len(applicable_rules),
            confidence_score=round(overall_confidence, 4),
            is_stub=False,
            stub_notice=None,
            notes=notes,
        )


# Module-level singleton (loaded once)
_engine_instance: Optional[RuleEngine] = None


def get_rule_engine() -> RuleEngine:
    """Get or create the module-level rule engine singleton."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = RuleEngine()
    return _engine_instance
