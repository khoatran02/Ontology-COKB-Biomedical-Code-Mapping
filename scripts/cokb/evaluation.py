from __future__ import annotations

import ast
from collections import Counter
from typing import Any, Iterable

from scripts.cokb.model import CodeConcept, MappingAssertion, MappingLevel
from scripts.cokb.reasoner import COKBReasoner


EVALUATED_LEVELS = ("A", "B", "C")


def _safe_ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_label_pairs(records: Iterable[dict[str, Any]]) -> dict[str, Any]:
    reasoner = COKBReasoner()
    confusion: Counter[tuple[str, str]] = Counter()
    predictions: list[dict[str, str]] = []

    for index, record in enumerate(records):
        input_value = record.get("Input", record.get("input", {}))
        if isinstance(input_value, str):
            input_value = ast.literal_eval(input_value)
        gold = str(record.get("output", record.get("gold", ""))).strip().upper()
        mapping = MappingAssertion(
            mapping_id=f"evaluation-{index}",
            source=CodeConcept("SOURCE", f"S{index}", str(input_value["original_label"])),
            target=CodeConcept("TARGET", f"T{index}", str(input_value["mapped_label"])),
            evidence_source="mapping_level_gold_standard",
            asserted_by="evaluation_fixture",
        )
        assessment = reasoner.assess(mapping)
        predicted = assessment.level.value
        confusion[(gold, predicted)] += 1
        predictions.append(
            {
                "gold": gold,
                "predicted": predicted,
                "rule_id": assessment.proof.rule_id,
            }
        )

    total = len(predictions)
    assessed = sum(item["predicted"] in EVALUATED_LEVELS for item in predictions)
    correct = sum(item["gold"] == item["predicted"] for item in predictions)
    metrics: dict[str, dict[str, float]] = {}
    for level in EVALUATED_LEVELS:
        true_positive = confusion[(level, level)]
        predicted_total = sum(confusion[(gold, level)] for gold in EVALUATED_LEVELS)
        gold_total = sum(confusion[(level, predicted)] for predicted in (*EVALUATED_LEVELS, "UNASSESSED"))
        precision = _safe_ratio(true_positive, predicted_total)
        recall = _safe_ratio(true_positive, gold_total)
        metrics[level] = {
            "precision": precision,
            "recall": recall,
            "f1": _safe_ratio(2 * precision * recall, precision + recall),
        }

    return {
        "total": total,
        "coverage": _safe_ratio(assessed, total),
        "overall_accuracy": _safe_ratio(correct, total),
        "accuracy_when_assessed": _safe_ratio(correct, assessed),
        "unassessed_count": total - assessed,
        "per_level": metrics,
        "confusion": {
            f"{gold}->{predicted}": count
            for (gold, predicted), count in sorted(confusion.items())
        },
        "predictions": predictions,
    }


def evaluate_mapping_level_xlsx(path: str) -> dict[str, Any]:
    from scripts.cokb.xlsx import read_first_sheet_records

    return evaluate_label_pairs(read_first_sheet_records(path))
