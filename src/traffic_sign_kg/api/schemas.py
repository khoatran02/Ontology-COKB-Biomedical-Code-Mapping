from typing import Any

from pydantic import BaseModel, Field


class InterpretSignRequest(BaseModel):
    class_id: int = Field(ge=0, le=51)


class EvaluateManeuverRequest(InterpretSignRequest):
    vehicle: str = Field(default="PassengerCar", min_length=1)
    maneuver: str = Field(min_length=1)


class ProblemResponse(BaseModel):
    problem_id: str
    status: str
    answer: str
    fact_count: int
    step_count: int
    explanation: dict[str, Any]


class CatalogEntryResponse(BaseModel):
    class_id: int
    class_uri: str
    raw_code: str
    label_vi: str
    label_en: str
    family: str
    rule_uri: str | None
    mapping_status: str
