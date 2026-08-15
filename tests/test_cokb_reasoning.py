from traffic_sign_kg.cokb import CokbEngine, Fact, FactKind, Goal, Problem, ProblemStatus
from traffic_sign_kg.cokb.domain import build_default_rules, build_registry
from traffic_sign_kg.cokb.problems import KnowledgeObject
from traffic_sign_kg.mapping.catalog import RULE, VKO, SignCatalog
from traffic_sign_kg.mapping.reasoning_mapper import ReasoningRdfMapper
from traffic_sign_kg.services.problem_service import ProblemService


def test_cokb_profile_exposes_six_component_runtime(catalog: SignCatalog):
    registry = build_registry()
    assert len(FactKind) == 12
    assert "InterpretSign" in registry.operation_ids
    assert "EvaluateManeuver" in registry.operation_ids
    assert "rulesOf" in registry.function_ids
    assert len(build_default_rules()) >= 8
    assert catalog.static_facts()


def test_p1_interpret_no_right_turn(catalog: SignCatalog):
    answer = ProblemService(catalog).interpret_sign(32)

    assert answer.result.status == ProblemStatus.PROVED
    assert answer.answer.endswith("/rule/no-right-turn")
    assert [step["rule_id"] for step in answer.explanation["steps"]] == ["R-SIGN-001"]


def test_p2_evaluate_maneuver_with_vehicle_taxonomy(catalog: SignCatalog):
    answer = ProblemService(catalog).evaluate_maneuver(32, "PassengerCar", "TurnRight")

    assert answer.result.status == ProblemStatus.PROVED
    assert answer.answer == "PROHIBITED"
    rule_ids = {step["rule_id"] for step in answer.explanation["steps"]}
    assert {"R-SIGN-001", "R-MAN-001", "R-VEH-001", "R-STATUS-001"} <= rule_ids

    trace_graph = ReasoningRdfMapper().result_graph(answer.result, "test-run")
    assert len(trace_graph) > 0
    assert str(trace_graph.identifier).endswith("/graph/inferred/test-run")


def test_p3_effective_speed_limit(catalog: SignCatalog):
    answer = ProblemService(catalog).effective_restriction(38)

    assert answer.result.status == ProblemStatus.PROVED
    assert answer.answer == "50 km/h"
    assert answer.explanation["steps"][-1]["rule_id"] == "R-NUM-001"


def test_open_world_absence_is_unknown(catalog: SignCatalog):
    answer = ProblemService(catalog).evaluate_maneuver(0, "PassengerCar", "TurnRight")
    assert answer.result.status == ProblemStatus.UNKNOWN
    assert answer.answer == "UNKNOWN"


def test_explicit_negative_fact_disproves_goal():
    goal = Goal("conveysRule", ("urn:sign", "urn:rule"))
    problem = Problem(
        problem_id="explicit-negative",
        problem_type="InterpretSign",
        objects=(KnowledgeObject("urn:sign", "TrafficSignOccurrence"),),
        facts=(Fact("not:conveysRule", goal.arguments),),
        goals=(goal,),
    )

    result = CokbEngine(build_default_rules()).solve(problem)

    assert result.status == ProblemStatus.DISPROVED


def test_conflicting_prohibition_and_obligation_is_inconsistent(catalog: SignCatalog):
    sign = "urn:test:sign"
    vehicle = "urn:test:vehicle"
    facts = (
        *catalog.static_facts(),
        Fact("conveysRule", (sign, str(RULE["no-right-turn"]))),
        Fact("conveysRule", (sign, str(RULE["left-turn-only"]))),
        Fact("requiresManeuver", (str(RULE["left-turn-only"]), str(VKO.TurnRight))),
        Fact("type", (vehicle, str(VKO.Vehicle)), FactKind.TYPE),
    )
    problem = Problem(
        problem_id="conflict",
        problem_type="EvaluateManeuver",
        objects=(KnowledgeObject(sign, "TrafficSignOccurrence"),),
        facts=facts,
        goals=(Goal("maneuverStatus", (sign, vehicle, str(VKO.TurnRight), "PROHIBITED")),),
    )

    result = CokbEngine(build_default_rules()).solve(problem)

    assert result.status == ProblemStatus.INCONSISTENT
    assert result.conflicts
