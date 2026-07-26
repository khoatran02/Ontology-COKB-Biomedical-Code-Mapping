from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class VectorBuildItem:
    rdf_uri: str
    entity_type: str
    vector: list[float]
    text: str | None = None
    image_uri: str | None = None
    region_uri: str | None = None
    asset_path: str | None = None
    class_uri: str | None = None
    sign_family_uri: str | None = None
    split: str | None = None
    source_type: str | None = None
    content_hash: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class VectorCandidate:
    faiss_id: int
    rdf_uri: str
    score: float
    index_name: str
    index_version: str
    entity_type: str
    graph_version: str
    class_uri: str | None = None
    asset_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class IndexVersion:
    index_name: str
    version: str
    file_path: Path
    file_sha256: str
    dimension: int
    metric: str
    index_factory: str
    embedding_model_id: str
    embedding_revision: str
    preprocessing_version: str
    graph_version: str
    item_count: int
    status: str


@dataclass(frozen=True, slots=True)
class BuiltIndex:
    version: IndexVersion
    item_ids: tuple[int, ...]
