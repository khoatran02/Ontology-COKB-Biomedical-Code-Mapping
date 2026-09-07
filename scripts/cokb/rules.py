from __future__ import annotations

from dataclasses import dataclass

from scripts.cokb.model import MappingAssertion, MappingLevel, Premise
from scripts.cokb.operators import (
    find_explicit_conflicts,
    labels_are_equivalent,
    labels_have_compatible_specificity,
    labels_share_generalized_condition,
    normalize_label,
)


@dataclass(frozen=True)
class RuleMatch:
    rule_id: str
    level: MappingLevel
    explanation: str
    premises: tuple[Premise, ...]


class MappingRule:
    rule_id = ""

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch | None:
        raise NotImplementedError


class ExactLabelRule(MappingRule):
    rule_id = "R-EXACT-LABEL"

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch | None:
        if not labels_are_equivalent(mapping.source.label, mapping.target.label):
            return None
        normalized = normalize_label(mapping.source.label)
        return RuleMatch(
            rule_id=self.rule_id,
            level=MappingLevel.EXACT,
            explanation="The normalized source and target labels are identical.",
            premises=(
                Premise("normalizedSourceLabel", normalized, mapping.evidence_source),
                Premise("normalizedTargetLabel", normalized, mapping.evidence_source),
            ),
        )


class ExplicitConflictRule(MappingRule):
    rule_id = "R-EXPLICIT-QUALIFIER-CONFLICT"

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch | None:
        conflicts = find_explicit_conflicts(mapping.source.label, mapping.target.label)
        if not conflicts:
            return None
        return RuleMatch(
            rule_id=self.rule_id,
            level=MappingLevel.CONFLICTING,
            explanation="The source and target labels contain incompatible qualifiers.",
            premises=(
                Premise("sourceLabel", mapping.source.label, mapping.evidence_source),
                Premise("targetLabel", mapping.target.label, mapping.evidence_source),
                Premise("detectedConflicts", conflicts, self.rule_id),
            ),
        )


class CompatibleSpecificityRule(MappingRule):
    rule_id = "R-COMPATIBLE-SPECIFICITY"

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch | None:
        if not labels_have_compatible_specificity(mapping.source.label, mapping.target.label):
            return None
        return RuleMatch(
            rule_id=self.rule_id,
            level=MappingLevel.PARTIAL,
            explanation="One label is a non-conflicting specialization of the other.",
            premises=(
                Premise("sourceLabel", mapping.source.label, mapping.evidence_source),
                Premise("targetLabel", mapping.target.label, mapping.evidence_source),
                Premise("explicitConflict", False, self.rule_id),
            ),
        )


class GeneralizedConditionRule(MappingRule):
    rule_id = "R-GENERALIZED-CONDITION"

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch | None:
        if not labels_share_generalized_condition(mapping.source.label, mapping.target.label):
            return None
        return RuleMatch(
            rule_id=self.rule_id,
            level=MappingLevel.PARTIAL,
            explanation="The labels share a condition term, while one is explicitly generalized.",
            premises=(
                Premise("sourceLabel", mapping.source.label, mapping.evidence_source),
                Premise("targetLabel", mapping.target.label, mapping.evidence_source),
                Premise("explicitConflict", False, self.rule_id),
            ),
        )


class UnassessedRule(MappingRule):
    rule_id = "R-INSUFFICIENT-EVIDENCE"

    def evaluate(self, mapping: MappingAssertion) -> RuleMatch:
        return RuleMatch(
            rule_id=self.rule_id,
            level=MappingLevel.UNASSESSED,
            explanation="The deterministic rule set has insufficient evidence to assign A, B, or C.",
            premises=(
                Premise("sourceLabel", mapping.source.label, mapping.evidence_source),
                Premise("targetLabel", mapping.target.label, mapping.evidence_source),
            ),
        )


DEFAULT_RULES: tuple[MappingRule, ...] = (
    ExactLabelRule(),
    ExplicitConflictRule(),
    CompatibleSpecificityRule(),
    GeneralizedConditionRule(),
    UnassessedRule(),
)
