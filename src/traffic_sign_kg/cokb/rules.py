from dataclasses import dataclass

from traffic_sign_kg.cokb.facts import FactKind, Term


def is_variable(term: Term) -> bool:
    return isinstance(term, str) and term.startswith("?")


@dataclass(frozen=True, slots=True)
class Atom:
    predicate: str
    arguments: tuple[Term, ...]
    kind: FactKind = FactKind.RELATION


@dataclass(frozen=True, slots=True)
class KnowledgeRule:
    rule_id: str
    premises: tuple[Atom, ...]
    conclusion: Atom
    priority: int = 0
    description: str = ""

    def __post_init__(self) -> None:
        if not self.rule_id:
            raise ValueError("rule_id must not be empty")
        if not self.premises:
            raise ValueError("rule must contain at least one premise")
