from __future__ import annotations

from pathlib import Path
from typing import Iterable


def validate_shacl(
    data_paths: Iterable[str | Path],
    ontology_path: str | Path,
    shapes_path: str | Path,
) -> tuple[bool, str, str]:
    """Run standards-based SHACL validation when the optional extras are installed."""
    try:
        from pyshacl import validate
        from rdflib import Graph
    except ImportError as error:
        raise RuntimeError(
            "SHACL dependencies are not installed. Install with: pip install -e '.[validation]'"
        ) from error

    data_graph = Graph()
    for path in data_paths:
        data_graph.parse(str(path), format="turtle")

    ontology_graph = Graph()
    ontology_graph.parse(str(ontology_path), format="turtle")
    shapes_graph = Graph()
    shapes_graph.parse(str(shapes_path), format="turtle")

    conforms, report_graph, report_text = validate(
        data_graph=data_graph,
        shacl_graph=shapes_graph,
        ont_graph=ontology_graph,
        inference="rdfs",
        abort_on_first=False,
        allow_infos=True,
        allow_warnings=True,
    )
    return bool(conforms), report_graph.serialize(format="turtle"), str(report_text)
