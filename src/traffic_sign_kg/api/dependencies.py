from dataclasses import dataclass

from fastapi import Request
from rdflib import Graph

from traffic_sign_kg.config import Settings
from traffic_sign_kg.mapping.catalog import SignCatalog
from traffic_sign_kg.repositories.fuseki_repository import FusekiRepository
from traffic_sign_kg.services.knowledge_service import KnowledgeService
from traffic_sign_kg.services.problem_service import ProblemService


@dataclass(slots=True)
class ApplicationContainer:
    settings: Settings
    catalog: SignCatalog
    problem_service: ProblemService
    knowledge_service: KnowledgeService
    ontology_graph: Graph
    shapes_graph: Graph
    fuseki: FusekiRepository


async def get_container(request: Request) -> ApplicationContainer:
    return request.app.state.container
