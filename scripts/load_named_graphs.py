import argparse
import asyncio
from pathlib import Path

from rdflib import Graph

from traffic_sign_kg.config import Settings
from traffic_sign_kg.repositories.fuseki_repository import FusekiRepository

GRAPHS = {
    "https://w3id.org/vn-ts-cokb/graph/ontology": "ontology/traffic-sign-ontology.ttl",
    "https://w3id.org/vn-ts-cokb/graph/catalog": (
        "ontology/catalog/vietnamese-sign-catalog.ttl"
    ),
}


async def load(root: Path, settings: Settings) -> None:
    repository = FusekiRepository(
        settings.fuseki_query_url,
        settings.fuseki_update_url,
        settings.fuseki_gsp_url,
        settings.fuseki_timeout_seconds,
    )
    for graph_uri, relative_path in GRAPHS.items():
        graph = Graph().parse(root / relative_path)
        payload = graph.serialize(format="turtle", encoding="utf-8")
        await repository.put_graph(graph_uri, payload, "text/turtle")
        print(f"loaded {len(graph)} triples into {graph_uri}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Load versioned ontology graphs into Fuseki")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    asyncio.run(load(args.root, Settings()))


if __name__ == "__main__":
    main()
