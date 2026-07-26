from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="TSKG_",
        extra="ignore",
    )

    app_name: str = "Ontology-Grounded Traffic Sign Knowledge Graph"
    environment: str = "development"
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "INFO"

    runtime_dir: Path = Path("runtime")
    operations_db: Path = Path("runtime/operations.db")
    vector_index_dir: Path = Path("runtime/vector-indexes")
    asset_dir: Path = Path("data")

    fuseki_query_url: str = "http://localhost:3030/traffic-signs/query"
    fuseki_update_url: str = "http://localhost:3030/traffic-signs/update"
    fuseki_gsp_url: str = "http://localhost:3030/traffic-signs/data"
    fuseki_timeout_seconds: float = Field(default=10.0, gt=0)

    allow_deterministic_embeddings: bool = True
    default_embedding_dimension: int = Field(default=64, ge=8)

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, value: str) -> str:
        value = value.lower()
        if value not in {"development", "test", "production"}:
            raise ValueError("environment must be development, test, or production")
        return value

    def ensure_runtime_directories(self) -> None:
        self.runtime_dir.mkdir(parents=True, exist_ok=True)
        self.operations_db.parent.mkdir(parents=True, exist_ok=True)
        self.vector_index_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
