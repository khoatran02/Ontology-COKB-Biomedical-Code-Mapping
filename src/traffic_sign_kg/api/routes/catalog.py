from typing import Annotated

from fastapi import APIRouter, Depends

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container
from traffic_sign_kg.api.schemas import CatalogEntryResponse

router = APIRouter(prefix="/catalog", tags=["semantic catalog"])


@router.get("", response_model=list[CatalogEntryResponse])
async def list_catalog(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> list[CatalogEntryResponse]:
    return [
        CatalogEntryResponse(
            class_id=entry.class_id,
            class_uri=str(entry.class_uri),
            raw_code=entry.raw_code,
            label_vi=entry.label_vi,
            label_en=entry.label_en,
            family=entry.family,
            rule_uri=str(entry.rule_uri) if entry.rule_uri else None,
            mapping_status=entry.mapping_status,
        )
        for entry in container.catalog.entries
    ]
