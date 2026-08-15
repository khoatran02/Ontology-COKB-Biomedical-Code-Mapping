from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class KnowledgeFunction:
    function_id: str
    input_types: tuple[str, ...]
    output_type: str
    handler: Callable[..., Any]
    version: str = "1.0.0"


@dataclass(frozen=True, slots=True)
class KnowledgeOperation:
    operation_id: str
    input_types: tuple[str, ...]
    output_type: str
    handler: Callable[..., Any]
    version: str = "1.0.0"


class KnowledgeRegistry:
    def __init__(self) -> None:
        self._functions: dict[str, KnowledgeFunction] = {}
        self._operations: dict[str, KnowledgeOperation] = {}

    def register_function(self, function: KnowledgeFunction) -> None:
        if function.function_id in self._functions:
            raise ValueError(f"duplicate knowledge function: {function.function_id}")
        self._functions[function.function_id] = function

    def register_operation(self, operation: KnowledgeOperation) -> None:
        if operation.operation_id in self._operations:
            raise ValueError(f"duplicate knowledge operation: {operation.operation_id}")
        self._operations[operation.operation_id] = operation

    def function(self, function_id: str) -> KnowledgeFunction:
        try:
            return self._functions[function_id]
        except KeyError as exc:
            raise KeyError(f"unknown knowledge function: {function_id}") from exc

    def operation(self, operation_id: str) -> KnowledgeOperation:
        try:
            return self._operations[operation_id]
        except KeyError as exc:
            raise KeyError(f"unknown knowledge operation: {operation_id}") from exc

    @property
    def function_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._functions))

    @property
    def operation_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._operations))
