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
    return {
        "status": "ready",
        "capabilities": {
            "local_cokb_reasoning": True,
            "owl_catalog": len(container.catalog.entries) == 52,
            "shacl_validation": True,
            "fuseki": fuseki_ready,
            "vector": False,
        },
    }
