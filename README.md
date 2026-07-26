# Ontology-Grounded Traffic Sign Knowledge Graph

Backend foundation for representing, validating, reasoning over, and hybrid-retrieving
Vietnamese traffic signs.

Storage architecture:

- Apache Jena Fuseki/TDB2 is the RDF/OWL source of truth.
- FAISS is a derived vector index.
- SQLite stores jobs, `faiss_id ↔ rdf_uri` mappings, and index manifests.
- The file system stores images/crops. The base source does not ingest datasets yet.

## Run locally

Requires Python 3.11–3.13. Example with `uv`:

```bash
uv venv --python 3.12
uv sync --extra dev --extra validation
cp .env.example .env
uv run traffic-sign-kg
```

Open:

```text
http://localhost:8000/docs
http://localhost:8000/api/v1/health/live
http://localhost:8000/api/v1/health/ready
```

Start Fuseki:

```bash
docker compose -f deployment/compose.yaml up -d fuseki
```

Load the base ontology:

```bash
./scripts/load_ontology.sh
```

## Smoke test without dataset/model

The development profile includes `DeterministicEmbeddingProvider`. This provider only
builds stable vectors from text so you can exercise the pipeline; it must not be used
as research results.

```bash
curl -X POST http://localhost:8000/api/v1/vector-indexes/ontology-concepts/rebuild \
  -H 'content-type: application/json' \
  -d '{
    "dimension": 64,
    "model_id": "deterministic-dev",
    "model_revision": "v1",
    "items": [
      {
        "rdf_uri": "https://example.org/traffic-sign-kg/ontology#ProhibitionSign",
        "entity_type": "ontology_class",
        "text": "biển báo cấm"
      }
    ]
  }'
```

Then:

```bash
curl -X POST http://localhost:8000/api/v1/search/vector \
  -H 'content-type: application/json' \
  -d '{
    "index_name": "ontology-concepts",
    "text": "biển cấm",
    "candidate_limit": 10
  }'
```

## Real dataset and model

Dataset adapters, YOLO parsing, crop generation, and pretrained embedding models are
left for a later phase. Adapters must produce stable RDF URIs and `VectorBuildItem`
records; they must not write ontology facts directly into FAISS.

Detailed docs:

- [Architecture](docs/architecture.md)
- [Proposal](docs/Ontology-Grounded-Traffic-Sign-Knowledge-Graph-Proposal.md)
