from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container
from traffic_sign_kg.api.schemas import IndexBuildResponse, RebuildIndexRequest
from traffic_sign_kg.domain.models import VectorBuildItem
from traffic_sign_kg.services.embedding import DeterministicEmbeddingProvider

router = APIRouter(prefix="/vector-indexes", tags=["vector-indexes"])


@router.get("")
async def list_indexes(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> list[dict[str, object]]:
    return container.operations.status()


@router.post("/{index_name}/rebuild", response_model=IndexBuildResponse)
async def rebuild_index(
    index_name: str,
    request: RebuildIndexRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> IndexBuildResponse:
    text_values = [item.text for item in request.items if item.text is not None]
    text_vectors: list[list[float]] = []
    if text_values:
        if not container.settings.allow_deterministic_embeddings:
            raise ValueError("text embedding is disabled; submit precomputed vectors")
        provider = DeterministicEmbeddingProvider(request.dimension)
        text_vectors = provider.embed_texts(text_values)
    vector_iterator = iter(text_vectors)
    items = [
        VectorBuildItem(
            rdf_uri=str(item.rdf_uri),
            entity_type=item.entity_type,
            vector=item.vector if item.vector is not None else next(vector_iterator),
            text=item.text,
            image_uri=str(item.image_uri) if item.image_uri else None,
            region_uri=str(item.region_uri) if item.region_uri else None,
            asset_path=item.asset_path,
            class_uri=str(item.class_uri) if item.class_uri else None,
            sign_family_uri=str(item.sign_family_uri) if item.sign_family_uri else None,
            split=item.split,
            source_type=item.source_type,
            content_hash=item.content_hash,
            metadata=item.metadata,
        )
        for item in request.items
    ]
    if any(len(item.vector) != request.dimension for item in items):
        raise ValueError("all vectors must match the requested dimension")
    built = await run_in_threadpool(
        container.vectors.build_and_activate,
        index_name,
        items,
        embedding_model_id=request.model_id,
        embedding_revision=request.model_revision,
        embedding_schema_version=request.embedding_schema_version,
        preprocessing_version=request.preprocessing_version,
        graph_version=request.graph_version,
        version=request.version,
    )
    return IndexBuildResponse(
        index_name=built.version.index_name,
        index_version=built.version.version,
        dimension=built.version.dimension,
        item_count=built.version.item_count,
        file_sha256=built.version.file_sha256,
        status=built.version.status,
    )
