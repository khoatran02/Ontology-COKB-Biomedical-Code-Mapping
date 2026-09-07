from __future__ import annotations

from pathlib import Path

from scripts.cokb.model import CodeConcept, MappingAssertion
from scripts.cokb.repository import COKBRepository


MAPPING_QUERY = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX map: <http://iqvia.com/ontologies/mappings/>

SELECT DISTINCT ?mapping ?sourceCode ?sourceLabel ?targetCode ?targetLabel
WHERE {
  GRAPH ?graph {
    ?mapping map:mapsFrom ?source ; map:mapsTo ?target .
    ?source map:mappedValue ?sourceCode .
    ?target map:mappedValue ?targetCode .
    OPTIONAL { ?source rdfs:label ?sourceLabel }
    OPTIONAL { ?target rdfs:label ?targetLabel }
  }
}
ORDER BY ?sourceCode ?targetCode
"""


def _term_value(solution, key: str) -> str:
    try:
        term = solution[key]
    except (KeyError, TypeError):
        return ""
    if term is None:
        return ""
    return str(getattr(term, "value", term)).strip()


def import_oxigraph_store(
    graph_store: str | Path,
    source_system: str,
    target_system: str,
    evidence_source: str,
) -> COKBRepository:
    """Convert the repository's mapping vocabulary into canonical COKB assertions."""
    try:
        from pyoxigraph import Store
    except ImportError as error:
        raise RuntimeError("pyoxigraph is required to import an Oxigraph store") from error

    store = Store.read_only(str(graph_store))
    return repository_from_solutions(
        store.query(MAPPING_QUERY),
        source_system=source_system,
        target_system=target_system,
        evidence_source=evidence_source,
    )


def repository_from_solutions(
    solutions,
    source_system: str,
    target_system: str,
    evidence_source: str,
) -> COKBRepository:
    mappings: list[MappingAssertion] = []
    seen: set[tuple[str, str, str, str]] = set()
    for solution in solutions:
        source_code = _term_value(solution, "sourceCode")
        target_code = _term_value(solution, "targetCode")
        source_label = _term_value(solution, "sourceLabel")
        target_label = _term_value(solution, "targetLabel")
        key = (source_system, source_code, target_system, target_code)
        if key in seen:
            continue
        seen.add(key)
        mappings.append(
            MappingAssertion(
                source=CodeConcept(source_system, source_code, source_label),
                target=CodeConcept(target_system, target_code, target_label),
                evidence_source=evidence_source,
                asserted_by="oxigraph_importer",
            )
        )
    return COKBRepository(mappings=mappings)
