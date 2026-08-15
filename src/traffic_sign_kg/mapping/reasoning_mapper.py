from rdflib import RDF, XSD, Graph, Literal, Namespace, URIRef

from traffic_sign_kg.cokb.facts import Fact
from traffic_sign_kg.cokb.problems import ProblemResult

VKO = Namespace("https://w3id.org/vn-ts-cokb/ontology#")
VKR = "https://w3id.org/vn-ts-cokb/resource"


class ReasoningRdfMapper:
    """Persist an auditable COKB run as an immutable inferred named graph."""

    def result_graph(self, result: ProblemResult, run_id: str) -> Graph:
        run_uri = URIRef(f"{VKR}/inference-run/{run_id}")
        graph = Graph(identifier=URIRef(f"https://w3id.org/vn-ts-cokb/graph/inferred/{run_id}"))
        graph.bind("vko", VKO)
        graph.add((run_uri, RDF.type, VKO.InferenceRun))
        graph.add((run_uri, VKO.problemId, Literal(result.problem_id)))
        graph.add((run_uri, VKO.reasoningStatus, Literal(result.status.value)))
        for step in result.steps:
            step_uri = URIRef(f"{run_uri}/step/{step.sequence}")
            graph.add((run_uri, VKO.hasInferenceStep, step_uri))
            graph.add((step_uri, RDF.type, VKO.InferenceStep))
            graph.add((step_uri, VKO.sequenceNumber, Literal(step.sequence, datatype=XSD.integer)))
            graph.add((step_uri, VKO.appliedRule, VKO[step.rule_id.replace("-", "_")]))
            conclusion_uri = self._add_fact(graph, step.conclusion)
            graph.add((step_uri, VKO.generatedConclusion, conclusion_uri))
            for premise in step.premises:
                graph.add((step_uri, VKO.usedPremise, self._add_fact(graph, premise)))
        return graph

    @staticmethod
    def _add_fact(graph: Graph, fact: Fact) -> URIRef:
        fact_uri = URIRef(f"{VKR}/fact/{fact.fact_id}")
        graph.add((fact_uri, RDF.type, VKO.Fact))
        graph.add((fact_uri, VKO.factKind, Literal(fact.kind.value)))
        graph.add((fact_uri, VKO.predicateName, Literal(fact.predicate)))
        for argument in fact.arguments:
            graph.add((fact_uri, VKO.argumentValue, Literal(str(argument))))
        return fact_uri
