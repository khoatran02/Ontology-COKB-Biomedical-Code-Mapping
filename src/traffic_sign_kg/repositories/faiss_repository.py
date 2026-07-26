import hashlib
import json
import os
import shutil
import tempfile
import threading
from datetime import UTC, datetime
from pathlib import Path

import faiss
import numpy as np

from traffic_sign_kg.domain.models import (
    BuiltIndex,
    IndexVersion,
    VectorBuildItem,
    VectorCandidate,
)
from traffic_sign_kg.repositories.operations_repository import OperationsRepository


class VectorIndexError(RuntimeError):
    pass


def _safe_index_name(value: str) -> str:
    if not value or any(char not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for char in value):
        raise ValueError("index_name may contain lowercase letters, digits, '-' and '_' only")
    return value


def _safe_version(value: str) -> str:
    if (
        not value
        or value in {".", ".."}
        or any(
            char not in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_."
            for char in value
        )
    ):
        raise ValueError("version may contain letters, digits, '-', '_' and '.' only")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FaissVectorRepository:
    """Immutable, versioned FAISS indexes with SQLite metadata mapping."""

    def __init__(self, index_root: Path, operations: OperationsRepository) -> None:
        self.index_root = index_root
        self.index_root.mkdir(parents=True, exist_ok=True)
        self.operations = operations
        self._loaded: dict[tuple[str, str], faiss.Index] = {}
        self._lock = threading.RLock()

    def build_version(
        self,
        index_name: str,
        items: list[VectorBuildItem],
        *,
        embedding_model_id: str,
        embedding_revision: str,
        embedding_schema_version: str,
        preprocessing_version: str,
        graph_version: str,
        version: str | None = None,
    ) -> BuiltIndex:
        index_name = _safe_index_name(index_name)
        if not items:
            raise ValueError("at least one vector item is required")
        if len({item.rdf_uri for item in items}) != len(items):
            raise ValueError("rdf_uri must be unique inside an index version")

        matrix = np.asarray([item.vector for item in items], dtype=np.float32)
        if matrix.ndim != 2 or matrix.shape[1] == 0:
            raise ValueError("vectors must form a non-empty two-dimensional matrix")
        if not np.isfinite(matrix).all():
            raise ValueError("vectors must contain only finite values")
        norms = np.linalg.norm(matrix, axis=1)
        if np.any(norms == 0):
            raise ValueError("zero vectors cannot be normalized for cosine similarity")
        faiss.normalize_L2(matrix)

        faiss_ids = np.asarray(
            [
                self.operations.reserve_faiss_id(
                    item.rdf_uri,
                    index_name,
                    embedding_schema_version,
                )
                for item in items
            ],
            dtype=np.int64,
        )

        dimension = int(matrix.shape[1])
        base_index = faiss.IndexFlatIP(dimension)
        index = faiss.IndexIDMap2(base_index)
        index.add_with_ids(matrix, faiss_ids)

        version = _safe_version(version or self._new_version(embedding_schema_version))
        final_directory = self.index_root / index_name / version
        if final_directory.exists():
            raise ValueError(f"index version already exists: {index_name}/{version}")
        final_directory.parent.mkdir(parents=True, exist_ok=True)
        temporary_directory = Path(
            tempfile.mkdtemp(prefix=f".{version}-", dir=final_directory.parent)
        )

        try:
            index_file = temporary_directory / "index.faiss"
            faiss.write_index(index, str(index_file))
            checksum = _sha256(index_file)
            manifest = {
                "index_name": index_name,
                "version": version,
                "dimension": dimension,
                "metric": "cosine_via_normalized_inner_product",
                "index_factory": "IndexIDMap2(IndexFlatIP)",
                "embedding_model_id": embedding_model_id,
                "embedding_revision": embedding_revision,
                "embedding_schema_version": embedding_schema_version,
                "preprocessing_version": preprocessing_version,
                "graph_version": graph_version,
                "item_count": len(items),
                "file_sha256": checksum,
            }
            (temporary_directory / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )
            os.rename(temporary_directory, final_directory)
        except Exception:
            shutil.rmtree(temporary_directory, ignore_errors=True)
            raise

        version_record = IndexVersion(
            index_name=index_name,
            version=version,
            file_path=final_directory / "index.faiss",
            file_sha256=checksum,
            dimension=dimension,
            metric="cosine_via_normalized_inner_product",
            index_factory="IndexIDMap2(IndexFlatIP)",
            embedding_model_id=embedding_model_id,
            embedding_revision=embedding_revision,
            preprocessing_version=preprocessing_version,
            graph_version=graph_version,
            item_count=len(items),
            status="ready",
        )
        try:
            self.operations.register_ready_version(
                version_record,
                embedding_schema_version,
                list(zip(faiss_ids.tolist(), items, strict=True)),
            )
        except Exception:
            shutil.rmtree(final_directory, ignore_errors=True)
            raise
        return BuiltIndex(version=version_record, item_ids=tuple(faiss_ids.tolist()))

    def activate_version(self, index_name: str, version: str) -> IndexVersion:
        index_name = _safe_index_name(index_name)
        record = self.operations.get_version(index_name, version)
        if record is None:
            raise ValueError(f"unknown index version: {index_name}/{version}")
        loaded = self._load_verified(record)
        self.operations.activate_version(index_name, version)
        with self._lock:
            self._loaded[(index_name, version)] = loaded
            stale_keys = [key for key in self._loaded if key[0] == index_name and key[1] != version]
            for key in stale_keys:
                del self._loaded[key]
        active = self.operations.get_active_version(index_name)
        if active is None:
            raise VectorIndexError("activation completed without an active manifest record")
        return active

    def build_and_activate(
        self,
        index_name: str,
        items: list[VectorBuildItem],
        **metadata: str,
    ) -> BuiltIndex:
        built = self.build_version(index_name, items, **metadata)
        active = self.activate_version(index_name, built.version.version)
        return BuiltIndex(version=active, item_ids=built.item_ids)

    def search(
        self,
        index_name: str,
        vector: list[float],
        candidate_limit: int,
    ) -> list[VectorCandidate]:
        index_name = _safe_index_name(index_name)
        if candidate_limit < 1:
            raise ValueError("candidate_limit must be positive")
        version = self.operations.get_active_version(index_name)
        if version is None:
            raise VectorIndexError(f"no active index: {index_name}")
        index = self._get_or_load(version)

        query = np.asarray([vector], dtype=np.float32)
        if query.shape != (1, version.dimension):
            raise ValueError(
                f"query dimension {query.shape[-1]} does not match index dimension "
                f"{version.dimension}"
            )
        if not np.isfinite(query).all() or float(np.linalg.norm(query)) == 0:
            raise ValueError("query vector must be finite and non-zero")
        faiss.normalize_L2(query)
        effective_limit = min(candidate_limit, max(version.item_count, 1))
        scores, ids = index.search(query, effective_limit)
        ids_and_scores = [
            (int(faiss_id), float(score))
            for faiss_id, score in zip(ids[0], scores[0], strict=True)
            if int(faiss_id) >= 0
        ]
        return self.operations.map_candidates(index_name, version.version, ids_and_scores)

    def is_ready(self, index_name: str) -> bool:
        try:
            version = self.operations.get_active_version(_safe_index_name(index_name))
            if version is None:
                return False
            self._get_or_load(version)
            return True
        except (OSError, ValueError, VectorIndexError):
            return False

    def _get_or_load(self, version: IndexVersion) -> faiss.Index:
        key = (version.index_name, version.version)
        with self._lock:
            loaded = self._loaded.get(key)
            if loaded is None:
                loaded = self._load_verified(version)
                self._loaded[key] = loaded
            return loaded

    @staticmethod
    def _load_verified(version: IndexVersion) -> faiss.Index:
        if not version.file_path.is_file():
            raise VectorIndexError(f"index file is missing: {version.file_path}")
        actual_checksum = _sha256(version.file_path)
        if actual_checksum != version.file_sha256:
            raise VectorIndexError(
                f"index checksum mismatch for {version.index_name}/{version.version}"
            )
        try:
            loaded = faiss.read_index(str(version.file_path))
        except RuntimeError as exc:
            raise VectorIndexError(f"cannot read FAISS index: {exc}") from exc
        if loaded.d != version.dimension or loaded.ntotal != version.item_count:
            raise VectorIndexError("FAISS index dimensions/count do not match manifest")
        return loaded

    @staticmethod
    def _new_version(embedding_schema_version: str) -> str:
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        safe_schema = "".join(
            char if char.isalnum() or char in "-_" else "-" for char in embedding_schema_version
        )
        return f"{safe_schema}-{timestamp}"
