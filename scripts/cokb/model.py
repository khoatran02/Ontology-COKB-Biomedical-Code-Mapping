from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from hashlib import sha256
from typing import Any


class MappingLevel(str, Enum):
    EXACT = "A"
    PARTIAL = "B"
    CONFLICTING = "C"
    UNASSESSED = "UNASSESSED"


class AssessmentType(str, Enum):
    RULE_BASED = "rule_based"
    MODEL = "model"
    HUMAN = "human"


@dataclass(frozen=True)
class CodeConcept:
    system: str
    code: str
    label: str

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "CodeConcept":
        return cls(
            system=str(value.get("system", "")).strip(),
            code=str(value.get("code", "")).strip(),
            label=str(value.get("label", "")).strip(),
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


def stable_mapping_id(source: CodeConcept, target: CodeConcept) -> str:
    raw = "|".join((source.system, source.code, target.system, target.code))
    return f"mapping-{sha256(raw.encode('utf-8')).hexdigest()[:16]}"


@dataclass(frozen=True)
class MappingAssertion:
    source: CodeConcept
    target: CodeConcept
    evidence_source: str
    mapping_id: str = ""
    asserted_by: str = "source_graph"

    def __post_init__(self) -> None:
        if not self.mapping_id:
            object.__setattr__(self, "mapping_id", stable_mapping_id(self.source, self.target))

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "MappingAssertion":
        return cls(
            mapping_id=str(value.get("mapping_id", "")).strip(),
            source=CodeConcept.from_dict(value.get("source", {})),
            target=CodeConcept.from_dict(value.get("target", {})),
            evidence_source=str(value.get("evidence_source", "")).strip(),
            asserted_by=str(value.get("asserted_by", "source_graph")).strip(),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "source": self.source.to_dict(),
            "target": self.target.to_dict(),
            "evidence_source": self.evidence_source,
            "asserted_by": self.asserted_by,
        }


@dataclass(frozen=True)
class Premise:
    predicate: str
    value: Any
    source: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProofTrace:
    conclusion: dict[str, Any]
    premises: tuple[Premise, ...]
    rule_id: str
    sources: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "conclusion": self.conclusion,
            "premises": [premise.to_dict() for premise in self.premises],
            "rule_id": self.rule_id,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class MappingAssessment:
    mapping_id: str
    level: MappingLevel
    assessment_type: AssessmentType
    explanation: str
    proof: ProofTrace

    def to_dict(self) -> dict[str, Any]:
        return {
            "mapping_id": self.mapping_id,
            "level": self.level.value,
            "assessment_type": self.assessment_type.value,
            "explanation": self.explanation,
            "proof": self.proof.to_dict(),
        }


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    severity: str = "error"
    mapping_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def conforms(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "conforms": self.conforms,
            "error_count": sum(issue.severity == "error" for issue in self.issues),
            "warning_count": sum(issue.severity == "warning" for issue in self.issues),
            "issues": [issue.to_dict() for issue in self.issues],
        }
