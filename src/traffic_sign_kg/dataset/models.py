from pathlib import Path
from typing import Self

from pydantic import BaseModel, Field, HttpUrl, model_validator


class BoundingBox(BaseModel):
    x_min: int = Field(ge=0)
    y_min: int = Field(ge=0)
    x_max: int = Field(gt=0)
    y_max: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered_coordinates(self) -> Self:
        if self.x_min >= self.x_max or self.y_min >= self.y_max:
            raise ValueError("bbox must satisfy x_min < x_max and y_min < y_max")
        return self


class NormalizedObservation(BaseModel):
    dataset_id: str = Field(min_length=1)
    image_id: str = Field(min_length=1)
    region_id: str = Field(min_length=1)
    image_path: Path
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    raw_class_code: str = Field(min_length=1)
    class_uri: HttpUrl
    bbox: BoundingBox
    provenance_uri: HttpUrl
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def bbox_inside_image(self) -> Self:
        if self.bbox.x_max > self.image_width or self.bbox.y_max > self.image_height:
            raise ValueError("bbox exceeds image dimensions")
        return self
