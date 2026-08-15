import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import TypeAlias

Term: TypeAlias = str | int | float | Decimal | bool


class FactKind(StrEnum):
    """The twelve event families used by the COKB profile."""

    TYPE = "type"
    DETERMINED = "determined"
    VALUE = "value"
    EQUALITY = "equality"
    DEPENDENCY = "dependency"
    RELATION = "relation"
    FUNCTION_DEFINED = "function_defined"
    FUNCTION_VALUE = "function_value"
    OBJECT_FUNCTION_EQUALITY = "object_function_equality"
    FUNCTION_EQUALITY = "function_equality"
    FUNCTION_DEPENDENCY = "function_dependency"
    FUNCTION_RELATION = "function_relation"


@dataclass(frozen=True, slots=True)
class Fact:
    predicate: str
    arguments: tuple[Term, ...]
    kind: FactKind = FactKind.RELATION
    asserted: bool = True
    source: str | None = None

    def __post_init__(self) -> None:
        if not self.predicate:
            raise ValueError("fact predicate must not be empty")
        if not self.arguments:
            raise ValueError("fact must have at least one argument")

    @property
    def fact_id(self) -> str:
        payload = json.dumps(
            [self.kind.value, self.predicate, [str(value) for value in self.arguments]],
            ensure_ascii=False,
            separators=(",", ":"),
        )
        return f"fact-{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:20]}"

    def same_statement(self, other: "Fact") -> bool:
        return self.predicate == other.predicate and self.arguments == other.arguments

    def statement_key(self) -> tuple[str, tuple[Term, ...]]:
        return self.predicate, self.arguments
