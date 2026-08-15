from typing import Annotated

from fastapi import APIRouter, Depends

from traffic_sign_kg.api.dependencies import ApplicationContainer, get_container
from traffic_sign_kg.api.schemas import (
    EvaluateManeuverRequest,
    InterpretSignRequest,
    ProblemResponse,
)
from traffic_sign_kg.services.problem_service import SemanticAnswer

router = APIRouter(prefix="/problems", tags=["COKB problems"])


def _response(answer: SemanticAnswer) -> ProblemResponse:
    return ProblemResponse(
        problem_id=answer.result.problem_id,
        status=answer.result.status.value,
        answer=answer.answer,
        fact_count=int(answer.result.metadata["fact_count"]),
        step_count=int(answer.result.metadata["step_count"]),
        explanation=answer.explanation,
    )


@router.post("/interpret-sign", response_model=ProblemResponse)
async def interpret_sign(
    request: InterpretSignRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ProblemResponse:
    return _response(container.problem_service.interpret_sign(request.class_id))


@router.post("/evaluate-maneuver", response_model=ProblemResponse)
async def evaluate_maneuver(
    request: EvaluateManeuverRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ProblemResponse:
    return _response(
        container.problem_service.evaluate_maneuver(
            request.class_id,
            request.vehicle,
            request.maneuver,
        )
    )


@router.post("/effective-restriction", response_model=ProblemResponse)
async def effective_restriction(
    request: InterpretSignRequest,
    container: Annotated[ApplicationContainer, Depends(get_container)],
) -> ProblemResponse:
    return _response(container.problem_service.effective_restriction(request.class_id))
