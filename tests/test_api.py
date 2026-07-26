from fastapi.testclient import TestClient

from traffic_sign_kg.config import Settings
from traffic_sign_kg.main import create_app


def test_vector_index_smoke_flow(tmp_path):
    settings = Settings(
        _env_file=None,
        environment="test",
        runtime_dir=tmp_path,
        operations_db=tmp_path / "operations.db",
        vector_index_dir=tmp_path / "vector-indexes",
        asset_dir=tmp_path / "assets",
        fuseki_timeout_seconds=0.1,
        default_embedding_dimension=64,
    )
    app = create_app(settings)

    with TestClient(app) as client:
        build_response = client.post(
            "/api/v1/vector-indexes/ontology-concepts/rebuild",
            json={
                "dimension": 64,
                "model_id": "deterministic-dev",
                "model_revision": "v1",
                "items": [
                    {
                        "rdf_uri": ("https://example.org/traffic-sign-kg/ontology#ProhibitionSign"),
                        "entity_type": "ontology_class",
                        "text": "biển báo cấm",
                    },
                    {
                        "rdf_uri": ("https://example.org/traffic-sign-kg/ontology#WarningSign"),
                        "entity_type": "ontology_class",
                        "text": "biển cảnh báo nguy hiểm",
                    },
                ],
            },
        )
        assert build_response.status_code == 200, build_response.text
        assert build_response.json()["status"] == "active"

        search_response = client.post(
            "/api/v1/search/vector",
            json={
                "index_name": "ontology-concepts",
                "text": "biển báo cấm",
                "candidate_limit": 2,
            },
        )
        assert search_response.status_code == 200, search_response.text
        payload = search_response.json()
        assert payload["verified_by_knowledge_graph"] is False
        assert payload["results"][0]["rdf_uri"].endswith("#ProhibitionSign")


def test_liveness(tmp_path):
    settings = Settings(
        _env_file=None,
        environment="test",
        runtime_dir=tmp_path,
        operations_db=tmp_path / "operations.db",
        vector_index_dir=tmp_path / "vector-indexes",
    )
    with TestClient(create_app(settings)) as client:
        response = client.get("/api/v1/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
