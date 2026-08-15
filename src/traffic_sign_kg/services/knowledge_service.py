from dataclasses import dataclass

from owlrl import DeductiveClosure, OWLRL_Semantics
from rdflib import Graph


@dataclass(frozen=True, slots=True)
class ValidationResult:
    conforms: bool
    report_graph: Graph
    report_text: str


class KnowledgeService:
    """Local RDF validation/reasoning boundary used before Fuseki materialization."""

    def validate(
        self,
        data_graph: Graph,
        shapes_graph: Graph,
        ontology_graph: Graph | None = None,
    ) -> ValidationResult:
        try:
            from pyshacl import validate
        except ImportError as exc:
            raise RuntimeError(
                "SHACL validation requires the 'validation' dependency extra"
            ) from exc
        conforms, report_graph, report_text = validate(
            data_graph,
            shacl_graph=shapes_graph,
            ont_graph=ontology_graph,
            inference="rdfs",
            abort_on_first=False,
            allow_infos=True,
            allow_warnings=True,
        )
        return ValidationResult(bool(conforms), report_graph, str(report_text))

    def materialize_owl_rl(self, asserted_graph: Graph) -> Graph:
        inferred = Graph()
        for triple in asserted_graph:
            inferred.add(triple)
        DeductiveClosure(
            OWLRL_Semantics,
            axiomatic_triples=False,
            datatype_axioms=False,
        ).expand(inferred)
        return inferred
