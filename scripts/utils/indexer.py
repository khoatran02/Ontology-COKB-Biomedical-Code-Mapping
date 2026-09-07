from __future__ import annotations

import io
import logging
import os
from pathlib import Path
from pyoxigraph import NamedNode, Store

logger = logging.getLogger(__name__)

SAMPLE_TTL = """@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix meta: <http://iqvia.com/ontologies/metadata/> .
@prefix dc: <http://purl.org/dc/elements/1.1/> .
@prefix : <http://iqvia.com/ontologies/mappings/> .

# Mapping K05.1 -> DA0B.Y
:mapping-k05-1-da0b-y a :Mapping ;
    :mapsFrom :concept-icd10who-k05-1 ;
    :mapsTo :concept-icd11-da0b-y .

:concept-icd10who-k05-1 a :CodeConcept ;
    :mappedValue "K05.1" ;
    rdfs:label "Chronic gingivitis" .

:concept-icd11-da0b-y a :CodeConcept ;
    :mappedValue "DA0B.Y" ;
    rdfs:label "Chronic gingivitis" .

# Mapping K05.1 -> DA0Z
:mapping-k05-1-da0z a :Mapping ;
    :mapsFrom :concept-icd10who-k05-1 ;
    :mapsTo :concept-icd11-da0z .

:concept-icd11-da0z a :CodeConcept ;
    :mappedValue "DA0Z" ;
    rdfs:label "Diseases or disorders of orofacial complex, unspecified" .

# Mapping K25.9 -> DA60.Y
:mapping-k25-9-da60-y a :Mapping ;
    :mapsFrom :concept-icd10cm-k25-9 ;
    :mapsTo :concept-icd11-da60-y .

:concept-icd10cm-k25-9 a :CodeConcept ;
    :mappedValue "K25.9" ;
    rdfs:label "Gastric ulcer, unspecified as acute or chronic, without hemorrhage or perforation" .

:concept-icd11-da60-y a :CodeConcept ;
    :mappedValue "DA60.Y" ;
    rdfs:label "Acute haemorrhagic gastric ulcer" .

# Mapping A31 -> 1B21.Z
:mapping-a31-1b21-z a :Mapping ;
    :mapsFrom :concept-icd10who-a31 ;
    :mapsTo :concept-icd11-1b21-z .

:concept-icd10who-a31 a :CodeConcept ;
    :mappedValue "A31" ;
    rdfs:label "Infection due to other mycobacteria" .

:concept-icd11-1b21-z a :CodeConcept ;
    :mappedValue "1B21.Z" ;
    rdfs:label "infection due to other mycobacteria" .

# Mapping A31 -> 1H0Z
:mapping-a31-1h0z a :Mapping ;
    :mapsFrom :concept-icd10who-a31 ;
    :mapsTo :concept-icd11-1h0z .

:concept-icd11-1h0z a :CodeConcept ;
    :mappedValue "1H0Z" ;
    rdfs:label "Infection, unspecified" .
"""


def is_git_lfs_pointer(filepath: Path | str) -> bool:
    try:
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline()
        return first_line.startswith("version https://git-lfs.github.com/spec/v1")
    except Exception:
        return False


def build_graph_store(graph_store_path: Path | str, source_ttl_dir: Path | str = None) -> Store:
    store_path = Path(graph_store_path)
    store_path.mkdir(parents=True, exist_ok=True)
    store = Store(str(store_path))

    target_graph = NamedNode("http://iqvia.com/ontologies/icd10cm_to_icd11_2024_full")

    loaded_any = False
    if source_ttl_dir and Path(source_ttl_dir).is_dir():
        for filename in os.listdir(source_ttl_dir):
            if filename.endswith(".ttl"):
                filepath = Path(source_ttl_dir, filename)
                graph_iri = NamedNode(f"http://iqvia.com/ontologies/{filename[:-4]}")
                if is_git_lfs_pointer(filepath):
                    logger.warning(
                        f"{filename} is a Git LFS pointer (not full TTL). "
                        f"Using sample mapping data into {graph_iri.value}."
                    )
                else:
                    try:
                        with open(filepath, "rb") as f:
                            store.load(f, "text/turtle", to_graph_name=graph_iri)
                        loaded_any = True
                        logger.info(f"Loaded {filename} into {graph_iri.value}")
                    except Exception as e:
                        logger.warning(f"Failed to load {filename}: {e}")

    if not loaded_any:
        # Load sample mappings into default graph and target named graph
        store.load(io.BytesIO(SAMPLE_TTL.encode("utf-8")), "text/turtle", to_graph_name=target_graph)
        logger.info(f"Populated Oxigraph store at {store_path} with sample mappings (K05.1, K25.9, A31)")

    return store


def ensure_graph_store(graph_data_path: Path | str) -> Store:
    path = Path(graph_data_path)
    if path.exists() and (path / "CURRENT").exists():
        return Store.read_only(str(path))

    logger.info(f"Oxigraph store not found at {path}. Initializing store...")
    source_ttl_dir = path.parent / "source_ttl"
    build_graph_store(path, source_ttl_dir=source_ttl_dir if source_ttl_dir.is_dir() else None)
    return Store.read_only(str(path))
