from pathlib import Path

import pytest

from traffic_sign_kg.mapping.catalog import SignCatalog

ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="session")
def catalog() -> SignCatalog:
    return SignCatalog.from_csv(ROOT / "ontology/catalog/vietnamese-sign-catalog.csv")
