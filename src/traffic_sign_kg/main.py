import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from traffic_sign_kg.api.dependencies import ApplicationContainer
from traffic_sign_kg.api.routes import health_router, indexes_router, search_router
from traffic_sign_kg.config import Settings, get_settings
from traffic_sign_kg.repositories.faiss_repository import (
    FaissVectorRepository,
    VectorIndexError,
)
from traffic_sign_kg.repositories.fuseki_repository import (
    FusekiRepository,
    FusekiUnavailableError,
)
from traffic_sign_kg.repositories.operations_repository import OperationsRepository
from traffic_sign_kg.services.embedding import DeterministicEmbeddingProvider
from traffic_sign_kg.services.query_service import QueryService


def build_container(settings: Settings) -> ApplicationContainer:
    settings.ensure_runtime_directories()
    operations = OperationsRepository(settings.operations_db)
    vectors = FaissVectorRepository(settings.vector_index_dir, operations)
    fuseki = FusekiRepository(
        settings.fuseki_query_url,
        settings.fuseki_update_url,
        settings.fuseki_gsp_url,
        settings.fuseki_timeout_seconds,
    )
    embeddings = (
        DeterministicEmbeddingProvider(settings.default_embedding_dimension)
        if settings.allow_deterministic_embeddings
        else None
    )
    queries = QueryService(vectors, fuseki)
    return ApplicationContainer(settings, operations, vectors, fuseki, embeddings, queries)


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_container(settings)
        yield

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description=(
            "RDF/OWL source of truth with FAISS candidate retrieval. "
            "Vector-only results are not knowledge-graph verified."
        ),
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(indexes_router, prefix="/api/v1")
    app.include_router(search_router, prefix="/api/v1")

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_REQUEST", "message": str(exc)}},
        )

    @app.exception_handler(VectorIndexError)
    async def vector_error_handler(_: Request, exc: VectorIndexError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "VECTOR_INDEX_UNAVAILABLE", "message": str(exc)}},
        )

    @app.exception_handler(FusekiUnavailableError)
    async def fuseki_error_handler(_: Request, exc: FusekiUnavailableError) -> JSONResponse:
        return JSONResponse(
            status_code=503,
            content={"error": {"code": "KNOWLEDGE_GRAPH_UNAVAILABLE", "message": str(exc)}},
        )

    return app


app = create_app()


def run() -> None:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level)
    uvicorn.run(
        "traffic_sign_kg.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    run()
