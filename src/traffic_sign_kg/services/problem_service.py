from __future__ import annotations

from dataclasses import dataclass

from traffic_sign_kg.cokb.domain import build_default_rules
from traffic_sign_kg.cokb.engine import CokbEngine
from traffic_sign_kg.cokb.explanation import explanation_payload
from traffic_sign_kg.cokb.facts import Fact, FactKind
from traffic_sign_kg.cokb.problems import Goal, KnowledgeObject, Problem, ProblemResult
from traffic_sign_kg.mapping.catalog import RULE_SEMANTICS, VKO, SignCatalog


@dataclass(frozen=True, slots=True)
class SemanticAnswer:
    answer: str
    result: ProblemResult
    explanation: dict[str, object]


class ProblemService:
    def __init__(self, catalog: SignCatalog) -> None:
        self.catalog = catalog
        self.engine = CokbEngine(build_default_rules())
        self.static_facts = catalog.static_facts()

    def interpret_sign(self, class_id: int) -> SemanticAnswer:
        entry = self.catalog.by_id(class_id)
        if entry.rule_uri is None:
            return self._unknown(class_id, "conveysRule", "UNKNOWN")
        sign_uri = self._sign_uri(class_id)
        result = self.engine.solve(
            self._problem(
                f"interpret-{class_id}",
                class_id,
                Goal("conveysRule", (sign_uri, str(entry.rule_uri))),
            )
        )
        return SemanticAnswer(str(entry.rule_uri), result, explanation_payload(result))

    def evaluate_maneuver(
        self,
        class_id: int,
        vehicle: str,
        maneuver: str,
    ) -> SemanticAnswer:
        sign_uri = self._sign_uri(class_id)
        vehicle_instance = f"urn:vehicle:{vehicle}"
        base_facts = (
            *self.static_facts,
            Fact("type", (sign_uri, str(self.catalog.by_id(class_id).class_uri)), FactKind.TYPE),
            Fact("type", (vehicle_instance, str(VKO[vehicle])), FactKind.TYPE),
        )
        conflicts: ProblemResult | None = None
        for answer in ("PROHIBITED", "REQUIRED"):
            result = self.engine.solve(
                Problem(
                    problem_id=f"maneuver-{class_id}-{vehicle}-{maneuver}-{answer.lower()}",
                    problem_type="EvaluateManeuver",
                    objects=(
                        KnowledgeObject(sign_uri, "TrafficSignOccurrence"),
                        KnowledgeObject(vehicle_instance, vehicle),
                    ),
                    facts=base_facts,
                    goals=(
                        Goal(
                            "maneuverStatus",
                            (sign_uri, vehicle_instance, str(VKO[maneuver]), answer),
                        ),
                    ),
                )
            )
            if result.status.value == "INCONSISTENT":
                conflicts = result
                break
            if result.status.value == "PROVED":
                return SemanticAnswer(answer, result, explanation_payload(result))
        result = conflicts or result
        answer = "INCONSISTENT" if conflicts else "UNKNOWN"
        return SemanticAnswer(answer, result, explanation_payload(result))

    def effective_restriction(self, class_id: int) -> SemanticAnswer:
        entry = self.catalog.by_id(class_id)
        if entry.rule_id is None:
            return self._unknown(class_id, "effectiveRestriction", "UNKNOWN")
        semantics = RULE_SEMANTICS[entry.rule_id]
        value = semantics.get("value")
        if value is None:
            return self._unknown(class_id, "effectiveRestriction", "UNKNOWN")
        sign_uri = self._sign_uri(class_id)
        goal = Goal(
            "effectiveRestriction",
            (sign_uri, value, str(VKO.KilometrePerHour)),
        )
        result = self.engine.solve(self._problem(f"restriction-{class_id}", class_id, goal))
        return SemanticAnswer(f"{value} km/h", result, explanation_payload(result))

    def _problem(self, problem_id: str, class_id: int, goal: Goal) -> Problem:
        sign_uri = self._sign_uri(class_id)
        entry = self.catalog.by_id(class_id)
        facts = (
            *self.static_facts,
            Fact("type", (sign_uri, str(entry.class_uri)), FactKind.TYPE, source="input"),
        )
        return Problem(
            problem_id=problem_id,
            problem_type="SemanticProblem",
            objects=(KnowledgeObject(sign_uri, "TrafficSignOccurrence"),),
            facts=facts,
            goals=(goal,),
        )

    def _unknown(self, class_id: int, predicate: str, answer: str) -> SemanticAnswer:
        sign_uri = self._sign_uri(class_id)
        result = self.engine.solve(
            self._problem(
                f"unknown-{predicate}-{class_id}",
                class_id,
                Goal(predicate, (sign_uri, "urn:unknown")),
            )
        )
        return SemanticAnswer(answer, result, explanation_payload(result))

    @staticmethod
    def _sign_uri(class_id: int) -> str:
        return f"https://w3id.org/vn-ts-cokb/resource/demo/sign-{class_id}"
