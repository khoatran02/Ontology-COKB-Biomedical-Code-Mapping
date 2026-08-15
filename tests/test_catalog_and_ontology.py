from pathlib import Path

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import OWL, RDF, Graph, URIRef

from traffic_sign_kg.mapping.catalog import VKO, SignCatalog

ROOT = Path(__file__).parents[1]


def test_catalog_has_exact_dataset_contract(catalog: SignCatalog):
    assert len(catalog.entries) == 52
    assert [entry.class_id for entry in catalog.entries] == list(range(52))
    assert catalog.by_id(32).raw_code == "P.123b"
    assert catalog.by_id(32).class_name == "NoRightTurnSign"
    assert catalog.by_id(16).mapping_status == "NeedsReview"


def test_core_and_generated_catalog_are_valid_owl(catalog: SignCatalog):
    core = Graph().parse(ROOT / "ontology/traffic-sign-ontology.ttl")
    catalog_graph = Graph().parse(ROOT / "ontology/catalog/vietnamese-sign-catalog.ttl")
    classes = set(catalog_graph.subjects(VKO.sourceClassId, None))

    assert len(core) > 300
    assert len(classes) == 52
    assert (VKO.NoRightTurnSign, RDF.type, OWL.Class) in catalog_graph


def test_owl_rl_materializes_rule_from_has_value_restriction():
    graph = Graph().parse(ROOT / "ontology/traffic-sign-ontology.ttl")
    graph.parse(ROOT / "ontology/catalog/vietnamese-sign-catalog.ttl")
    sign = URIRef("urn:test:sign")
    graph.add((sign, RDF.type, VKO.NoRightTurnSign))

    DeductiveClosure(OWLRL_Semantics).expand(graph)

    assert (
        sign,
        VKO.conveysRule,
        URIRef("https://w3id.org/vn-ts-cokb/resource/rule/no-right-turn"),
    ) in graph
