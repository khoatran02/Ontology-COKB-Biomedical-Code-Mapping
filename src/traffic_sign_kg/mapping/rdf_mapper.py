from decimal import Decimal

from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from traffic_sign_kg.dataset.models import NormalizedObservation
from traffic_sign_kg.mapping.uri_policy import resource_uri

VKO = Namespace("https://w3id.org/vn-ts-cokb/ontology#")


class RdfMapper:
    """Map evidence without collapsing observations, occurrences, and OWL classes."""

    def observation_graph(self, observation: NormalizedObservation) -> Graph:
        graph = Graph(identifier=URIRef("https://w3id.org/vn-ts-cokb/graph/asserted"))
        graph.bind("vko", VKO)
        image_uri = URIRef(
            resource_uri(
                "image",
                observation.dataset_id,
                observation.dataset_version,
                observation.image_id,
            )
        )
        region_uri = URIRef(
            resource_uri(
                "region",
                observation.dataset_id,
                observation.dataset_version,
                observation.image_id,
                observation.region_id,
            )
        )
        occurrence_uri = URIRef(f"{region_uri}/sign/v1")
        assertion_uri = URIRef(
            resource_uri(
                "assertion",
                str(observation.provenance_uri),
                str(region_uri),
                str(observation.class_uri),
            )
        )
        run_uri = URIRef(str(observation.provenance_uri))
        class_uri = URIRef(str(observation.class_uri))

        graph.add((image_uri, RDF.type, VKO.Image))
        graph.add((image_uri, VKO.hasRegion, region_uri))
        graph.add((image_uri, VKO.imageWidth, Literal(observation.image_width)))
        graph.add((image_uri, VKO.imageHeight, Literal(observation.image_height)))
        graph.add((image_uri, VKO.sourcePath, Literal(str(observation.image_path))))
        graph.add((image_uri, VKO.contentHash, Literal(observation.content_hash)))
        graph.add((image_uri, VKO.datasetId, Literal(observation.dataset_id)))
        graph.add((image_uri, VKO.datasetVersion, Literal(observation.dataset_version)))

        graph.add((region_uri, RDF.type, VKO.ImageRegion))
        graph.add((region_uri, VKO.regionOf, image_uri))
        graph.add((region_uri, VKO.depicts, occurrence_uri))
        graph.add((region_uri, VKO.xMin, Literal(observation.bbox.x_min)))
        graph.add((region_uri, VKO.yMin, Literal(observation.bbox.y_min)))
        graph.add((region_uri, VKO.xMax, Literal(observation.bbox.x_max)))
        graph.add((region_uri, VKO.yMax, Literal(observation.bbox.y_max)))

        graph.add((occurrence_uri, RDF.type, VKO.TrafficSignOccurrence))
        if observation.assertion_status == "Accepted":
            graph.add((occurrence_uri, RDF.type, class_uri))

        graph.add((assertion_uri, RDF.type, VKO.ClassificationAssertion))
        graph.add((assertion_uri, VKO.assertionSubject, occurrence_uri))
        graph.add((assertion_uri, VKO.assertedType, class_uri))
        graph.add((assertion_uri, VKO.generatedBy, run_uri))
        graph.add((assertion_uri, VKO.assertionStatus, VKO[observation.assertion_status]))
        graph.add(
            (
                assertion_uri,
                VKO.confidence,
                Literal(Decimal(str(observation.confidence)), datatype=XSD.decimal),
            )
        )
        graph.add((run_uri, RDF.type, VKO.DatasetAnnotationRun))
        graph.add((run_uri, VKO.datasetId, Literal(observation.dataset_id)))
        graph.add((run_uri, VKO.datasetVersion, Literal(observation.dataset_version)))
        return graph
