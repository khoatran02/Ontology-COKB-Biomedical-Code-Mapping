import pytest

from traffic_sign_kg.domain.models import VectorBuildItem
from traffic_sign_kg.repositories.faiss_repository import FaissVectorRepository
from traffic_sign_kg.repositories.operations_repository import OperationsRepository


def test_build_activate_search_and_keep_stable_ids(tmp_path):
    operations = OperationsRepository(tmp_path / "operations.db")
    vectors = FaissVectorRepository(tmp_path / "indexes", operations)
    items = [
        VectorBuildItem(
            rdf_uri="https://example.org/resource/a",
            entity_type="ontology_class",
            vector=[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ),
        VectorBuildItem(
            rdf_uri="https://example.org/resource/b",
            entity_type="ontology_class",
            vector=[0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        ),
    ]
    first = vectors.build_and_activate(
        "ontology-concepts",
        items,
        embedding_model_id="test",
        embedding_revision="1",
        embedding_schema_version="1",
        preprocessing_version="1",
        graph_version="kg-1",
        version="v1",
    )

    results = vectors.search(
        "ontology-concepts",
        [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
        2,
    )

    assert first.version.status == "active"
    assert results[0].rdf_uri == "https://example.org/resource/a"
    assert results[0].score == 1.0

    second = vectors.build_and_activate(
        "ontology-concepts",
        items,
        embedding_model_id="test",
        embedding_revision="2",
        embedding_schema_version="1",
        preprocessing_version="1",
        graph_version="kg-2",
        version="v2",
    )

    assert second.item_ids == first.item_ids
    assert operations.get_version("ontology-concepts", "v1").status == "archived"
    assert operations.get_active_version("ontology-concepts").version == "v2"


def test_rejects_zero_vectors(tmp_path):
    operations = OperationsRepository(tmp_path / "operations.db")
    vectors = FaissVectorRepository(tmp_path / "indexes", operations)

    try:
        vectors.build_version(
            "visual-assets",
            [
                VectorBuildItem(
                    rdf_uri="https://example.org/resource/a",
                    entity_type="observation",
                    vector=[0.0] * 8,
                )
            ],
            embedding_model_id="test",
            embedding_revision="1",
            embedding_schema_version="1",
            preprocessing_version="1",
            graph_version="kg-1",
        )
    except ValueError as exc:
        assert "zero vectors" in str(exc)
    else:
        raise AssertionError("zero vector must be rejected")


def test_rejects_version_path_traversal(tmp_path):
    operations = OperationsRepository(tmp_path / "operations.db")
    vectors = FaissVectorRepository(tmp_path / "indexes", operations)

    with pytest.raises(ValueError, match="version"):
        vectors.build_version(
            "visual-assets",
            [
                VectorBuildItem(
                    rdf_uri="https://example.org/resource/a",
                    entity_type="observation",
                    vector=[1.0] * 8,
                )
            ],
            embedding_model_id="test",
            embedding_revision="1",
            embedding_schema_version="1",
            preprocessing_version="1",
            graph_version="kg-1",
            version="../../outside",
        )
