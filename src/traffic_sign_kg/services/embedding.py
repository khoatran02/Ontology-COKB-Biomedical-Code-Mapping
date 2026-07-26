import hashlib
from typing import Protocol

import numpy as np


class EmbeddingProvider(Protocol):
    model_id: str
    revision: str
    dimension: int

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...

    def embed_images(self, image_paths: list[str]) -> list[list[float]]: ...


class DeterministicEmbeddingProvider:
    """Development-only provider; validates plumbing, not retrieval quality."""

    model_id = "deterministic-dev"
    revision = "v1"

    def __init__(self, dimension: int = 64) -> None:
        if dimension < 8:
            raise ValueError("dimension must be at least 8")
        self.dimension = dimension

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(value.encode("utf-8")) for value in texts]

    def embed_images(self, image_paths: list[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for image_path in image_paths:
            hasher = hashlib.sha256()
            with open(image_path, "rb") as stream:
                for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                    hasher.update(chunk)
            vectors.append(self._embed(hasher.digest()))
        return vectors

    def _embed(self, source: bytes) -> list[float]:
        raw = hashlib.shake_256(source).digest(self.dimension * 2)
        values = np.frombuffer(raw, dtype=np.uint16).astype(np.float32)
        values = (values / 32767.5) - 1.0
        norm = float(np.linalg.norm(values))
        if norm == 0:
            values[0] = 1.0
            norm = 1.0
        return (values / norm).tolist()
