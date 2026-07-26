from pathlib import Path

from rdflib import RDF, Graph, URIRef

from traffic_sign_kg.dataset.models import BoundingBox, NormalizedObservation
from traffic_sign_kg.mapping.rdf_mapper import VKO, RdfMapper
from traffic_sign_kg.services.knowledge_service import KnowledgeService

ROOT = Path(__file__).parents[1]


def test_ontology_and_shapes_are_valid_turtle():
    ontology = Graph().parse(ROOT / "ontology/traffic-sign-ontology.ttl")
    shapes = Graph().parse(ROOT / "ontology/traffic-sign-shapes.ttl")

    assert (
        VKO.TrafficSignObservation,
        RDF.type,
        URIRef("http://www.w3.org/2002/07/owl#Class"),
    ) in ontology
    assert len(shapes) > 0


def test_normalized_observation_maps_and_validates_with_shacl(tmp_path):
    observation = NormalizedObservation(
        dataset_id="future-dataset",
        image_id="image-1",
        region_id="region-1",
        image_path=tmp_path / "image.jpg",
        image_width=640,
        image_height=480,
        raw_class_code="P.123b",
        class_uri="https://example.org/traffic-sign-kg/ontology#ProhibitionSign",
        bbox=BoundingBox(x_min=10, y_min=20, x_max=110, y_max=120),
        provenance_uri="https://example.org/traffic-sign-kg/resource/annotation/a1",
        confidence=1.0,
    )
    data_graph = RdfMapper().observation_graph(observation)
    data_graph.parse(ROOT / "ontology/traffic-sign-ontology.ttl")
    shapes_graph = Graph().parse(ROOT / "ontology/traffic-sign-shapes.ttl")

    result = KnowledgeService().validate(data_graph, shapes_graph)

    assert result.conforms, result.report_text
    assert len(data_graph) > 0
