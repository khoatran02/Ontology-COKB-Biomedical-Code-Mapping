from dataclasses import dataclass

from fastapi import Request

from traffic_sign_kg.config import Settings
from traffic_sign_kg.repositories.faiss_repository import FaissVectorRepository
from traffic_sign_kg.repositories.fuseki_repository import FusekiRepository
from traffic_sign_kg.repositories.operations_repository import OperationsRepository
from traffic_sign_kg.services.embedding import EmbeddingProvider
from traffic_sign_kg.services.query_service import QueryService


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    operations: OperationsRepository
    vectors: FaissVectorRepository
    fuseki: FusekiRepository
    embeddings: EmbeddingProvider | None
    queries: QueryService


def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container
