from collections.abc import Iterable

from traffic_sign_kg.cokb.explanation import explanation_payload
from traffic_sign_kg.cokb.facts import Fact
from traffic_sign_kg.cokb.registry import (
    KnowledgeFunction,
    KnowledgeOperation,
    KnowledgeRegistry,
)
from traffic_sign_kg.cokb.rules import Atom, KnowledgeRule


def build_default_rules() -> tuple[KnowledgeRule, ...]:
    return (
        KnowledgeRule(
            "R-TAX-001",
            (Atom("type", ("?object", "?child")), Atom("subClassOf", ("?child", "?parent"))),
            Atom("type", ("?object", "?parent")),
            priority=10,
            description="Propagate instance type through the concept hierarchy.",
        ),
        KnowledgeRule(
            "R-SIGN-001",
            (Atom("type", ("?sign", "?class")), Atom("classConveysRule", ("?class", "?rule"))),
            Atom("conveysRule", ("?sign", "?rule")),
            priority=20,
            description="Attach the canonical traffic rule of a sign class to an occurrence.",
        ),
        KnowledgeRule(
            "R-MAN-001",
            (
                Atom("conveysRule", ("?sign", "?rule")),
                Atom("prohibitsManeuver", ("?rule", "?maneuver")),
            ),
            Atom("signProhibits", ("?sign", "?rule", "?maneuver")),
            priority=30,
        ),
        KnowledgeRule(
            "R-MAN-002",
            (
                Atom("conveysRule", ("?sign", "?rule")),
                Atom("requiresManeuver", ("?rule", "?maneuver")),
            ),
            Atom("signRequires", ("?sign", "?rule", "?maneuver")),
            priority=30,
        ),
        KnowledgeRule(
            "R-VEH-TAX-001",
            (
                Atom("type", ("?vehicle", "?child")),
                Atom("broaderVehicleCategory", ("?child", "?parent")),
            ),
            Atom("type", ("?vehicle", "?parent")),
            priority=15,
            description="Propagate a vehicle instance through the category hierarchy.",
        ),
        KnowledgeRule(
            "R-VEH-001",
            (
                Atom("appliesTo", ("?rule", "?vehicleClass")),
                Atom("type", ("?vehicle", "?vehicleClass")),
            ),
            Atom("applicableTo", ("?rule", "?vehicle")),
            priority=25,
        ),
        KnowledgeRule(
            "R-VEH-ACCESS-001",
            (
                Atom("conveysRule", ("?sign", "?rule")),
                Atom("prohibitsVehicleCategory", ("?rule", "?vehicleClass")),
                Atom("type", ("?vehicle", "?vehicleClass")),
            ),
            Atom("vehicleAccessStatus", ("?sign", "?vehicle", "PROHIBITED")),
            priority=100,
        ),
        KnowledgeRule(
            "R-STATUS-001",
            (
                Atom("signProhibits", ("?sign", "?rule", "?maneuver")),
                Atom("applicableTo", ("?rule", "?vehicle")),
            ),
            Atom("maneuverStatus", ("?sign", "?vehicle", "?maneuver", "PROHIBITED")),
            priority=100,
        ),
        KnowledgeRule(
            "R-STATUS-002",
            (
                Atom("signRequires", ("?sign", "?rule", "?maneuver")),
                Atom("applicableTo", ("?rule", "?vehicle")),
            ),
            Atom("maneuverStatus", ("?sign", "?vehicle", "?maneuver", "REQUIRED")),
            priority=100,
        ),
        KnowledgeRule(
            "R-NUM-001",
            (
                Atom("conveysRule", ("?sign", "?rule")),
                Atom("restrictionValue", ("?rule", "?value", "?unit")),
            ),
            Atom("effectiveRestriction", ("?sign", "?value", "?unit")),
            priority=80,
        ),
    )


def _objects_for(facts: Iterable[Fact], predicate: str, subject: str) -> tuple[object, ...]:
    return tuple(
        fact.arguments[1]
        for fact in facts
        if fact.predicate == predicate and len(fact.arguments) == 2 and fact.arguments[0] == subject
    )


def rules_of(facts: Iterable[Fact], sign_uri: str) -> tuple[object, ...]:
    return _objects_for(facts, "conveysRule", sign_uri)


def prohibited_maneuvers(facts: Iterable[Fact], rule_uri: str) -> tuple[object, ...]:
    return _objects_for(facts, "prohibitsManeuver", rule_uri)


def required_maneuvers(facts: Iterable[Fact], rule_uri: str) -> tuple[object, ...]:
    return _objects_for(facts, "requiresManeuver", rule_uri)


def applicable_vehicles(facts: Iterable[Fact], rule_uri: str) -> tuple[object, ...]:
    return _objects_for(facts, "appliesTo", rule_uri)


def is_applicable_to(facts: Iterable[Fact], rule_uri: str, vehicle_uri: str) -> bool | None:
    if any(
        fact.predicate == "applicableTo" and fact.arguments == (rule_uri, vehicle_uri)
        for fact in facts
    ):
        return True
    return None


def maneuver_status(
    facts: Iterable[Fact],
    sign_uri: str,
    vehicle_uri: str,
    maneuver_uri: str,
) -> str:
    statuses = {
        str(fact.arguments[3])
        for fact in facts
        if fact.predicate == "maneuverStatus"
        and fact.arguments[:3] == (sign_uri, vehicle_uri, maneuver_uri)
    }
    if {"PROHIBITED", "REQUIRED"} <= statuses:
        return "INCONSISTENT"
    return next(iter(statuses), "UNKNOWN")


def restriction_value(facts: Iterable[Fact], rule_uri: str) -> tuple[object, object] | None:
    for fact in facts:
        if fact.predicate == "restrictionValue" and fact.arguments[0] == rule_uri:
            return fact.arguments[1], fact.arguments[2]
    return None


def build_registry() -> KnowledgeRegistry:
    registry = KnowledgeRegistry()
    registry.register_function(
        KnowledgeFunction("rulesOf", ("TrafficSignOccurrence",), "TrafficRuleSet", rules_of)
    )
    registry.register_function(
        KnowledgeFunction(
            "requiredManeuvers",
            ("TrafficRule",),
            "ManeuverSet",
            required_maneuvers,
        )
    )
    registry.register_function(
        KnowledgeFunction(
            "applicableVehicles",
            ("TrafficRule",),
            "VehicleCategorySet",
            applicable_vehicles,
        )
    )
    registry.register_function(
        KnowledgeFunction(
            "isApplicableTo",
            ("TrafficRule", "VehicleCategory"),
            "BooleanOrUnknown",
            is_applicable_to,
        )
    )
    registry.register_function(
        KnowledgeFunction(
            "maneuverStatus",
            ("TrafficSignOccurrence", "VehicleCategory", "Maneuver"),
            "ManeuverStatus",
            maneuver_status,
        )
    )
    registry.register_function(
        KnowledgeFunction(
            "prohibitedManeuvers",
            ("TrafficRule",),
            "ManeuverSet",
            prohibited_maneuvers,
        )
    )
    registry.register_function(
        KnowledgeFunction(
            "restrictionValue",
            ("TrafficRule",),
            "QuantityOrUnknown",
            restriction_value,
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "EvaluateManeuver",
            ("Problem",),
            "ProblemResult",
            lambda engine, problem: engine.solve(problem),
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "InterpretSign",
            ("FactSet", "TrafficSignOccurrence"),
            "TrafficRuleSet",
            rules_of,
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "EvaluateVehicleApplicability",
            ("FactSet", "TrafficRule", "VehicleCategory"),
            "BooleanOrUnknown",
            is_applicable_to,
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "ResolveCompositeSign",
            ("FactSet", "TrafficRule"),
            "ManeuverSet",
            prohibited_maneuvers,
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "MaterializeKnowledge",
            ("CokbEngine", "Problem"),
            "ProblemResult",
            lambda engine, problem: engine.solve(problem),
        )
    )
    registry.register_operation(
        KnowledgeOperation(
            "ExplainConclusion",
            ("ProblemResult",),
            "Explanation",
            explanation_payload,
        )
    )
    return registry
