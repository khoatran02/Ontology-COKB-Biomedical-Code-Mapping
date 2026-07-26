import pytest

from traffic_sign_kg.services.query_service import QueryService


def test_query_templates_reject_sparql_injection():
    with pytest.raises(ValueError):
        QueryService._compile_template(
            "find_by_sign_family",
            {"sign_family_uri": "https://example.org/x> } UNION { ?s ?p ?o"},
            20,
        )


def test_find_by_maneuver_template():
    query = QueryService._compile_template(
        "find_by_maneuver",
        {"maneuver_uri": "https://example.org/traffic-sign-kg/ontology#TurnRight"},
        20,
    )

    assert "vko:prohibitsManeuver" in query
    assert "LIMIT 20" in query
