import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from rdflib import Graph

from traffic_sign_kg.api.dependencies import ApplicationContainer
from traffic_sign_kg.api.routes import (
    catalog_router,
    health_router,
    ingestions_router,
    problems_router,
)
from traffic_sign_kg.config import Settings, get_settings
from traffic_sign_kg.mapping.catalog import SignCatalog
from traffic_sign_kg.repositories.fuseki_repository import (
    FusekiRepository,
    FusekiUnavailableError,
)
from traffic_sign_kg.services.knowledge_service import KnowledgeService
from traffic_sign_kg.services.problem_service import ProblemService


def build_container(settings: Settings) -> ApplicationContainer:
    settings.ensure_runtime_directories()
    catalog = SignCatalog.from_csv(settings.catalog_path)
    ontology_graph = Graph().parse(settings.ontology_path)
    ontology_graph.parse(settings.catalog_ttl_path)
    shapes_graph = Graph().parse(settings.shapes_path)
    fuseki = FusekiRepository(
        settings.fuseki_query_url,
        settings.fuseki_update_url,
        settings.fuseki_gsp_url,
        settings.fuseki_timeout_seconds,
    )
    return ApplicationContainer(
        settings=settings,
        catalog=catalog,
        problem_service=ProblemService(catalog),
        knowledge_service=KnowledgeService(),
        ontology_graph=ontology_graph,
        shapes_graph=shapes_graph,
        fuseki=fuseki,
    )


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.container = build_container(settings)
        yield

    app = FastAPI(
        title=settings.app_name,
        version="1.0.0",
        description=(
            "COKB/OWL semantic demo for Vietnamese traffic signs. "
            "The MVP reasons from curated annotations and does not require a detector."
        ),
        lifespan=lifespan,
    )
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(catalog_router, prefix="/api/v1")
    app.include_router(problems_router, prefix="/api/v1")
    app.include_router(ingestions_router, prefix="/api/v1")

    @app.exception_handler(ValueError)
    async def value_error_handler(_: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "INVALID_REQUEST", "message": str(exc)}},
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
