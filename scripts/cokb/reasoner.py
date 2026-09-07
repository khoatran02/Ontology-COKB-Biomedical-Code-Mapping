from __future__ import annotations

from collections.abc import Iterable

from scripts.cokb.model import (
    AssessmentType,
    MappingAssessment,
    MappingAssertion,
    ProofTrace,
)
from scripts.cokb.rules import DEFAULT_RULES, MappingRule


class COKBReasoner:
    """Ordered, deterministic rule engine for mapping assessments."""

    def __init__(self, rules: Iterable[MappingRule] = DEFAULT_RULES) -> None:
        self.rules = tuple(rules)
        if not self.rules:
            raise ValueError("At least one mapping rule is required")

    def assess(self, mapping: MappingAssertion) -> MappingAssessment:
        for rule in self.rules:
            match = rule.evaluate(mapping)
            if match is None:
                continue
            conclusion = {
                "mapping_id": mapping.mapping_id,
                "predicate": "hasMappingLevel",
                "object": match.level.value,
            }
            proof = ProofTrace(
                conclusion=conclusion,
                premises=match.premises,
                rule_id=match.rule_id,
                sources=(mapping.evidence_source,),
            )
            return MappingAssessment(
                mapping_id=mapping.mapping_id,
                level=match.level,
                assessment_type=AssessmentType.RULE_BASED,
                explanation=match.explanation,
                proof=proof,
            )
        raise RuntimeError("Rule set did not produce an assessment")

    def assess_all(self, mappings: Iterable[MappingAssertion]) -> list[MappingAssessment]:
        return [self.assess(mapping) for mapping in mappings]
