from typing import Any, Self

from pydantic import BaseModel, Field, HttpUrl, model_validator


class VectorItemInput(BaseModel):
    rdf_uri: HttpUrl
    entity_type: str = Field(min_length=1, max_length=64)
    vector: list[float] | None = None
    text: str | None = Field(default=None, min_length=1)
    image_uri: HttpUrl | None = None
    region_uri: HttpUrl | None = None
    asset_path: str | None = None
    class_uri: HttpUrl | None = None
    sign_family_uri: HttpUrl | None = None
    split: str | None = None
    source_type: str | None = None
    content_hash: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def require_vector_or_text(self) -> Self:
        if (self.vector is None) == (self.text is None):
            raise ValueError("provide exactly one of vector or text")
        return self


class RebuildIndexRequest(BaseModel):
    dimension: int = Field(ge=8, le=65_536)
    model_id: str = Field(min_length=1)
    model_revision: str = Field(min_length=1)
    embedding_schema_version: str = "1"
    preprocessing_version: str = "1"
    graph_version: str = "unversioned"
    version: str | None = None
    items: list[VectorItemInput] = Field(min_length=1)


class IndexBuildResponse(BaseModel):
    index_name: str
    index_version: str
    dimension: int
    item_count: int
    file_sha256: str
    status: str


class VectorSearchRequest(BaseModel):
    index_name: str = Field(pattern=r"^[a-z0-9_-]+$")
    vector: list[float] | None = None
    text: str | None = Field(default=None, min_length=1)
    candidate_limit: int = Field(default=20, ge=1, le=1000)

    @model_validator(mode="after")
    def require_vector_or_text(self) -> Self:
        if (self.vector is None) == (self.text is None):
            raise ValueError("provide exactly one of vector or text")
        return self


class SemanticSearchRequest(BaseModel):
    template_id: str
    parameters: dict[str, str] = Field(default_factory=dict)
    limit: int = Field(default=20, ge=1, le=500)


class SemanticFilter(BaseModel):
    sign_family_uri: HttpUrl | None = None
    applies_to_uri: HttpUrl | None = None


class HybridSearchRequest(VectorSearchRequest):
    result_limit: int = Field(default=20, ge=1, le=500)
    semantic_filter: SemanticFilter = Field(default_factory=SemanticFilter)


class VectorCandidateResponse(BaseModel):
    faiss_id: int
    rdf_uri: str
    score: float
    index_name: str
    index_version: str
    entity_type: str
    graph_version: str
    class_uri: str | None = None
    asset_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    mode: str
    verified_by_knowledge_graph: bool
    results: list[VectorCandidateResponse] | list[dict[str, Any]]
