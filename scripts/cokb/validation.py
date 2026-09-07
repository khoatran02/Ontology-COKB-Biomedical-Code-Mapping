from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from scripts.cokb.model import MappingAssertion, ValidationIssue, ValidationReport
from scripts.cokb.operators import normalize_code


def validate_mappings(mappings: Iterable[MappingAssertion]) -> ValidationReport:
    materialized = list(mappings)
    issues: list[ValidationIssue] = []
    ids = Counter(mapping.mapping_id for mapping in materialized)

    for mapping in materialized:
        required = {
            "source.system": mapping.source.system,
            "source.code": mapping.source.code,
            "source.label": mapping.source.label,
            "target.system": mapping.target.system,
            "target.code": mapping.target.code,
            "target.label": mapping.target.label,
            "evidence_source": mapping.evidence_source,
        }
        for field_name, value in required.items():
            if not value:
                issues.append(
                    ValidationIssue(
                        code="COKB_REQUIRED_VALUE",
                        message=f"{field_name} must not be empty",
                        mapping_id=mapping.mapping_id,
                    )
                )
        if ids[mapping.mapping_id] > 1:
            issues.append(
                ValidationIssue(
                    code="COKB_DUPLICATE_MAPPING_ID",
                    message=f"mapping_id occurs {ids[mapping.mapping_id]} times",
                    mapping_id=mapping.mapping_id,
                )
            )
        if (
            mapping.source.system == mapping.target.system
            and normalize_code(mapping.source.code) == normalize_code(mapping.target.code)
        ):
            issues.append(
                ValidationIssue(
                    code="COKB_SELF_MAPPING",
                    message="source and target identify the same code concept",
                    severity="warning",
                    mapping_id=mapping.mapping_id,
                )
            )
    return ValidationReport(issues)
