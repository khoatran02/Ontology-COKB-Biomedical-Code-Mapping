from decimal import Decimal
from urllib.parse import quote

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from traffic_sign_kg.dataset.models import NormalizedObservation

VKO = Namespace("https://example.org/traffic-sign-kg/ontology#")
RESOURCE = "https://example.org/traffic-sign-kg/resource"


class RdfMapper:
    def observation_graph(self, observation: NormalizedObservation) -> Graph:
        graph = Graph()
        graph.bind("vko", VKO)
        observation_uri = URIRef(
            f"{RESOURCE}/observation/{quote(observation.dataset_id, safe='')}/"
            f"{quote(observation.region_id, safe='')}"
        )
        image_uri = URIRef(
            f"{RESOURCE}/image/{quote(observation.dataset_id, safe='')}/"
            f"{quote(observation.image_id, safe='')}"
        )
        bbox_uri = URIRef(f"{observation_uri}/bbox")

        graph.add((observation_uri, RDF.type, VKO.TrafficSignObservation))
        graph.add((observation_uri, VKO.observesSignType, URIRef(str(observation.class_uri))))
        graph.add((observation_uri, VKO.inImage, image_uri))
        graph.add((observation_uri, VKO.hasBoundingBox, bbox_uri))
        graph.add((observation_uri, VKO.generatedBy, URIRef(str(observation.provenance_uri))))
        graph.add(
            (
                observation_uri,
                VKO.confidence,
                Literal(Decimal(str(observation.confidence)), datatype=XSD.decimal),
            )
        )

        graph.add((image_uri, RDF.type, VKO.Image))
        graph.add((image_uri, VKO.depictsSign, observation_uri))

        graph.add((bbox_uri, RDF.type, VKO.BoundingBox))
        graph.add(
            (bbox_uri, VKO.xMin, Literal(observation.bbox.x_min, datatype=XSD.nonNegativeInteger))
        )
        graph.add(
            (bbox_uri, VKO.yMin, Literal(observation.bbox.y_min, datatype=XSD.nonNegativeInteger))
        )
        graph.add(
            (bbox_uri, VKO.xMax, Literal(observation.bbox.x_max, datatype=XSD.nonNegativeInteger))
        )
        graph.add(
            (bbox_uri, VKO.yMax, Literal(observation.bbox.y_max, datatype=XSD.nonNegativeInteger))
        )
        return graph
