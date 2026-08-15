from pathlib import Path

from traffic_sign_kg.mapping.catalog import SignCatalog


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "ontology/catalog/vietnamese-sign-catalog.csv"
    destination = root / "ontology/catalog/vietnamese-sign-catalog.ttl"
    catalog = SignCatalog.from_csv(source)
    catalog.to_graph().serialize(destination=destination, format="turtle")
    print(f"exported {len(catalog.entries)} classes to {destination}")


if __name__ == "__main__":
    main()
