import asyncio
from pathlib import Path

import httpx
import pytest

from traffic_sign_kg.config import Settings
from traffic_sign_kg.main import build_container, create_app
from traffic_sign_kg.services.query_service import QueryService

ROOT = Path(__file__).parents[1]


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        runtime_dir=tmp_path,
        dataset_dir=ROOT / "data/archive",
        ontology_path=ROOT / "ontology/traffic-sign-ontology.ttl",
        catalog_path=ROOT / "ontology/catalog/vietnamese-sign-catalog.csv",
        catalog_ttl_path=ROOT / "ontology/catalog/vietnamese-sign-catalog.ttl",
        shapes_path=ROOT / "ontology/traffic-sign-shapes.ttl",
        fuseki_timeout_seconds=0.01,
    )


def test_cokb_api_flow(tmp_path):
    settings = _settings(tmp_path)
    app = create_app(settings)
    container = build_container(settings)
    app.state.container = container
    paths = set(app.openapi()["paths"])

    maneuver = container.problem_service.evaluate_maneuver(32, "PassengerCar", "TurnRight")
    restriction = container.problem_service.effective_restriction(38)

    assert "/api/v1/catalog" in paths
    assert "/api/v1/problems/evaluate-maneuver" in paths
    assert len(container.catalog.entries) == 52
    assert maneuver.answer == "PROHIBITED" and maneuver.explanation["steps"]
    assert restriction.answer == "50 km/h"

    async def request_api() -> tuple[int, str]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/problems/evaluate-maneuver",
                json={"class_id": 32, "vehicle": "PassengerCar", "maneuver": "TurnRight"},
            )
            return response.status_code, response.json()["answer"]

    assert asyncio.run(request_api()) == (200, "PROHIBITED")


def test_semantic_query_is_scoped_and_rejects_injection():
    query = QueryService.compile_template(
        "signs_by_maneuver",
        {"maneuver_uri": "https://w3id.org/vn-ts-cokb/ontology#TurnRight"},
        20,
    )
    assert "graph/catalog" in query
    assert "graph/asserted" in query
    with pytest.raises(ValueError):
        QueryService.compile_template(
            "signs_by_family",
            {"family_uri": "https://example.org/x> } UNION { ?s ?p ?o"},
            20,
        )
