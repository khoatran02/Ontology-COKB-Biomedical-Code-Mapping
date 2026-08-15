from typing import Annotated

from fastapi import APIRouter, Depends, Query

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container
from traffic_sign_kg.dataset.yolo_adapter import YoloDatasetAdapter
from traffic_sign_kg.mapping.rdf_mapper import RdfMapper

router = APIRouter(prefix="/ingestions", tags=["dataset ingestion"])


@router.get("/profile")
async def profile_dataset(
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> dict[str, int]:
    profile = YoloDatasetAdapter(container.settings.dataset_dir, container.catalog).profile()
    return {
        "image_count": profile.image_count,
        "label_count": profile.label_count,
        "box_count": profile.box_count,
        "empty_label_count": profile.empty_label_count,
        "class_count": profile.class_count,
    }


@router.post("/validate-sample")
async def validate_sample(
    container: Annotated[ApplicationContainer, Depends(get_container)],
    limit: Annotated[int, Query(ge=1, le=100)] = 5,
) -> dict[str, object]:
    adapter = YoloDatasetAdapter(container.settings.dataset_dir, container.catalog)
    mapper = RdfMapper()
    accepted = review = quarantine = triples = 0
    reports: list[str] = []
    for observation in adapter.iter_observations(limit=limit):
        candidate = mapper.observation_graph(observation)
        result = container.knowledge_service.validate(
            candidate,
            container.shapes_graph,
            container.ontology_graph,
        )
        triples += len(candidate)
        if not result.conforms:
            quarantine += 1
            reports.append(result.report_text)
        elif observation.assertion_status == "PendingReview":
            review += 1
        else:
            accepted += 1
    return {
        "processed": accepted + review + quarantine,
        "accepted": accepted,
        "review": review,
        "quarantine": quarantine,
        "rdf_triples": triples,
        "validation_reports": reports,
    }
