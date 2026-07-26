from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container
from traffic_sign_kg.api.schemas import (
    HybridSearchRequest,
    SearchResponse,
    SemanticSearchRequest,
    VectorCandidateResponse,
    VectorSearchRequest,
)
from traffic_sign_kg.services.embedding import DeterministicEmbeddingProvider

router = APIRouter(prefix="/search", tags=["search"])


def _query_vector(
    request: VectorSearchRequest,
    container: ApplicationContainer,
) -> list[float]:
    if request.vector is not None:
        return request.vector
    if container.embeddings is None or request.text is None:
        raise ValueError("text embedding is unavailable; submit a query vector")
    if isinstance(container.embeddings, DeterministicEmbeddingProvider):
        active = container.operations.get_active_version(request.index_name)
        if active is None:
            raise ValueError(f"no active index: {request.index_name}")
        return DeterministicEmbeddingProvider(active.dimension).embed_texts([request.text])[0]
    return container.embeddings.embed_texts([request.text])[0]


@router.post("/vector", response_model=SearchResponse)
async def vector_search(
    request: VectorSearchRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SearchResponse:
    vector = _query_vector(request, container)
    candidates = await run_in_threadpool(
        container.queries.vector_search,
        request.index_name,
        vector,
        request.candidate_limit,
    )
    return SearchResponse(
        mode="vector",
        verified_by_knowledge_graph=False,
        results=[VectorCandidateResponse(**asdict(candidate)) for candidate in candidates],
    )


@router.post("/semantic", response_model=SearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SearchResponse:
    results = await container.queries.semantic_search(
        request.template_id,
        request.parameters,
        request.limit,
    )
    return SearchResponse(
        mode="semantic",
        verified_by_knowledge_graph=True,
        results=results,
    )


@router.post("/hybrid", response_model=SearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> SearchResponse:
    vector = _query_vector(request, container)
    candidates = await run_in_threadpool(
        container.queries.vector_search,
        request.index_name,
        vector,
        request.candidate_limit,
    )
    verified = await container.queries.hybrid_filter(
        candidates,
        sign_family_uri=(
            str(request.semantic_filter.sign_family_uri)
            if request.semantic_filter.sign_family_uri
            else None
        ),
        applies_to_uri=(
            str(request.semantic_filter.applies_to_uri)
            if request.semantic_filter.applies_to_uri
            else None
        ),
        result_limit=request.result_limit,
    )
    return SearchResponse(
        mode="hybrid",
        verified_by_knowledge_graph=True,
        results=[VectorCandidateResponse(**asdict(candidate)) for candidate in verified],
    )
