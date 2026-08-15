from dataclasses import dataclass, field
from enum import StrEnum

from traffic_sign_kg.cokb.facts import Fact, Term


class ProblemStatus(StrEnum):
    PROVED = "PROVED"
    DISPROVED = "DISPROVED"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True, slots=True)
class KnowledgeObject:
    object_id: str
    concept: str


@dataclass(frozen=True, slots=True)
class Goal:
    predicate: str
    arguments: tuple[Term, ...]

    def as_fact(self) -> Fact:
        return Fact(self.predicate, self.arguments, asserted=False)


@dataclass(frozen=True, slots=True)
class Problem:
    problem_id: str
    problem_type: str
    objects: tuple[KnowledgeObject, ...]
    facts: tuple[Fact, ...]
    goals: tuple[Goal, ...]
    context_graphs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.problem_id:
            raise ValueError("problem_id must not be empty")
        if not self.goals:
            raise ValueError("problem must contain at least one goal")


@dataclass(frozen=True, slots=True)
class InferenceStep:
    sequence: int
    rule_id: str
    premises: tuple[Fact, ...]
    conclusion: Fact


@dataclass(frozen=True, slots=True)
class ProblemResult:
    problem_id: str
    status: ProblemStatus
    goals: tuple[Goal, ...]
    facts: tuple[Fact, ...]
    steps: tuple[InferenceStep, ...]
    goal_facts: tuple[Fact, ...] = ()
    conflicts: tuple[tuple[Fact, ...], ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)
