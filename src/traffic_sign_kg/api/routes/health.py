from typing import Annotated

from fastapi import APIRouter, Depends

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "alive"}


@router.get("/ready")
async def ready(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> dict[str, object]:
    fuseki_ready = await container.fuseki.is_available()
    indexes = container.operations.status()
    active_indexes = [item for item in indexes if item["status"] == "active"]
    vector_ready = all(
        container.vectors.is_ready(str(item["index_name"])) for item in active_indexes
    )
    status = "ready" if fuseki_ready else "degraded"
    return {
        "status": status,
        "capabilities": {
            "semantic": fuseki_ready,
            "vector": vector_ready and bool(active_indexes),
        },
        "active_indexes": len(active_indexes),
    }
