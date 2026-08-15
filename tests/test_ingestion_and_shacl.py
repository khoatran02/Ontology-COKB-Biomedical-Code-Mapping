import hashlib
from pathlib import Path

from rdflib import Graph

from traffic_sign_kg.dataset.models import BoundingBox, NormalizedObservation
from traffic_sign_kg.dataset.yolo_adapter import YoloDatasetAdapter
from traffic_sign_kg.mapping.catalog import VKO, SignCatalog
from traffic_sign_kg.mapping.rdf_mapper import RdfMapper
from traffic_sign_kg.services.knowledge_service import KnowledgeService

ROOT = Path(__file__).parents[1]


def _ontology() -> Graph:
    graph = Graph().parse(ROOT / "ontology/traffic-sign-ontology.ttl")
    graph.parse(ROOT / "ontology/catalog/vietnamese-sign-catalog.ttl")
    return graph


def test_gold_and_invalid_fixtures_route_correctly():
    shapes = Graph().parse(ROOT / "ontology/traffic-sign-shapes.ttl")
    service = KnowledgeService()
    gold = Graph().parse(ROOT / "fixtures/gold/p123b-accepted.ttl")
    invalid = Graph().parse(ROOT / "fixtures/invalid/bbox-outside-image.ttl")

    assert service.validate(gold, shapes, _ontology()).conforms
    assert not service.validate(invalid, shapes, _ontology()).conforms


def test_normalized_observation_maps_to_separate_semantic_entities(tmp_path):
    digest = hashlib.sha256(b"fixture").hexdigest()
    observation = NormalizedObservation(
        dataset_id="fixture",
        dataset_version="v1",
        image_id="image-1",
        region_id="image-1-00",
        image_path=tmp_path / "image.jpg",
        image_width=640,
        image_height=480,
        source_class_id=32,
        raw_class_code="P.123b",
        class_uri=str(VKO.NoRightTurnSign),
        bbox=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=120),
        provenance_uri="https://w3id.org/vn-ts-cokb/resource/dataset-run/fixture-v1",
        confidence=1.0,
        content_hash=f"sha256:{digest}",
    )
    graph = RdfMapper().observation_graph(observation)
    shapes = Graph().parse(ROOT / "ontology/traffic-sign-shapes.ttl")

    assert KnowledgeService().validate(graph, shapes, _ontology()).conforms
    assert len(graph) >= 25


def test_dataset_profile_and_sample_ingestion(catalog: SignCatalog):
    adapter = YoloDatasetAdapter(ROOT / "data/archive", catalog)
    profile = adapter.profile()
    sample = next(iter(adapter.iter_observations(limit=1)))

    assert profile.image_count == 3216
    assert profile.label_count == 3216
    assert profile.box_count == 8334
    assert profile.empty_label_count == 25
    assert sample.bbox.x_max <= sample.image_width
    assert sample.bbox.y_max <= sample.image_height
