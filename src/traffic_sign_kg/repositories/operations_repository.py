import json
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from traffic_sign_kg.domain.models import IndexVersion, VectorBuildItem, VectorCandidate

SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS stable_vector_ids (
    faiss_id INTEGER PRIMARY KEY AUTOINCREMENT,
    rdf_uri TEXT NOT NULL,
    index_name TEXT NOT NULL,
    embedding_schema_version TEXT NOT NULL,
    UNIQUE (rdf_uri, index_name, embedding_schema_version)
);

CREATE TABLE IF NOT EXISTS vector_index_versions (
    index_name TEXT NOT NULL,
    version TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    metric TEXT NOT NULL,
    index_factory TEXT NOT NULL,
    embedding_model_id TEXT NOT NULL,
    embedding_revision TEXT NOT NULL,
    embedding_schema_version TEXT NOT NULL,
    preprocessing_version TEXT NOT NULL,
    item_count INTEGER NOT NULL,
    graph_version TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('building', 'ready', 'active', 'archived', 'failed')),
    created_at TEXT NOT NULL,
    activated_at TEXT,
    PRIMARY KEY (index_name, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_active_vector_index
ON vector_index_versions(index_name)
WHERE status = 'active';

CREATE TABLE IF NOT EXISTS vector_items (
    index_name TEXT NOT NULL,
    index_version TEXT NOT NULL,
    faiss_id INTEGER NOT NULL,
    rdf_uri TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    image_uri TEXT,
    region_uri TEXT,
    asset_path TEXT,
    class_uri TEXT,
    sign_family_uri TEXT,
    split TEXT,
    source_type TEXT,
    graph_version TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    PRIMARY KEY (index_name, index_version, faiss_id),
    FOREIGN KEY (index_name, index_version)
        REFERENCES vector_index_versions(index_name, version)
        ON DELETE CASCADE,
    FOREIGN KEY (faiss_id) REFERENCES stable_vector_ids(faiss_id)
);

CREATE INDEX IF NOT EXISTS idx_vector_items_rdf_uri
ON vector_items(rdf_uri);

CREATE INDEX IF NOT EXISTS idx_vector_items_lookup
ON vector_items(index_name, index_version, active, class_uri, split);

CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    job_type TEXT NOT NULL,
    status TEXT NOT NULL,
    payload_json TEXT NOT NULL DEFAULT '{}',
    error_message TEXT,
    attempt INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class OperationsRepository:
    """SQLite operational state; never the source of truth for domain facts."""

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self.initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock, self._connect() as connection:
            try:
                connection.execute("BEGIN IMMEDIATE")
                yield connection
                connection.commit()
            except Exception:
                connection.rollback()
                raise

    def initialize(self) -> None:
        with self._lock, self._connect() as connection:
            connection.executescript(SCHEMA)

    def reserve_faiss_id(
        self,
        rdf_uri: str,
        index_name: str,
        embedding_schema_version: str,
    ) -> int:
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT OR IGNORE INTO stable_vector_ids
                    (rdf_uri, index_name, embedding_schema_version)
                VALUES (?, ?, ?)
                """,
                (rdf_uri, index_name, embedding_schema_version),
            )
            row = connection.execute(
                """
                SELECT faiss_id FROM stable_vector_ids
                WHERE rdf_uri = ? AND index_name = ? AND embedding_schema_version = ?
                """,
                (rdf_uri, index_name, embedding_schema_version),
            ).fetchone()
            if row is None:
                raise RuntimeError("failed to reserve FAISS ID")
            return int(row["faiss_id"])

    def register_ready_version(
        self,
        version: IndexVersion,
        embedding_schema_version: str,
        items: Sequence[tuple[int, VectorBuildItem]],
    ) -> None:
        now = utc_now()
        with self.transaction() as connection:
            connection.execute(
                """
                INSERT INTO vector_index_versions (
                    index_name, version, file_path, file_sha256, dimension, metric,
                    index_factory, embedding_model_id, embedding_revision,
                    embedding_schema_version, preprocessing_version, item_count,
                    graph_version, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ready', ?)
                """,
                (
                    version.index_name,
                    version.version,
                    str(version.file_path),
                    version.file_sha256,
                    version.dimension,
                    version.metric,
                    version.index_factory,
                    version.embedding_model_id,
                    version.embedding_revision,
                    embedding_schema_version,
                    version.preprocessing_version,
                    version.item_count,
                    version.graph_version,
                    now,
                ),
            )
            connection.executemany(
                """
                INSERT INTO vector_items (
                    index_name, index_version, faiss_id, rdf_uri, entity_type,
                    image_uri, region_uri, asset_path, class_uri, sign_family_uri,
                    split, source_type, graph_version, content_hash, metadata_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        version.index_name,
                        version.version,
                        faiss_id,
                        item.rdf_uri,
                        item.entity_type,
                        item.image_uri,
                        item.region_uri,
                        item.asset_path,
                        item.class_uri,
                        item.sign_family_uri,
                        item.split,
                        item.source_type,
                        version.graph_version,
                        item.content_hash,
                        json.dumps(item.metadata, ensure_ascii=False, sort_keys=True),
                        now,
                    )
                    for faiss_id, item in items
                ],
            )

    def activate_version(self, index_name: str, version: str) -> None:
        now = utc_now()
        with self.transaction() as connection:
            target = connection.execute(
                """
                SELECT status FROM vector_index_versions
                WHERE index_name = ? AND version = ?
                """,
                (index_name, version),
            ).fetchone()
            if target is None or target["status"] not in {"ready", "active"}:
                raise ValueError(f"index version is not ready: {index_name}/{version}")
            connection.execute(
                """
                UPDATE vector_index_versions
                SET status = 'archived'
                WHERE index_name = ? AND status = 'active' AND version <> ?
                """,
                (index_name, version),
            )
            connection.execute(
                """
                UPDATE vector_index_versions
                SET status = 'active', activated_at = ?
                WHERE index_name = ? AND version = ?
                """,
                (now, index_name, version),
            )

    def get_active_version(self, index_name: str) -> IndexVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM vector_index_versions
                WHERE index_name = ? AND status = 'active'
                """,
                (index_name,),
            ).fetchone()
        return self._row_to_version(row) if row else None

    def get_version(self, index_name: str, version: str) -> IndexVersion | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM vector_index_versions
                WHERE index_name = ? AND version = ?
                """,
                (index_name, version),
            ).fetchone()
        return self._row_to_version(row) if row else None

    def map_candidates(
        self,
        index_name: str,
        index_version: str,
        ids_and_scores: Sequence[tuple[int, float]],
    ) -> list[VectorCandidate]:
        if not ids_and_scores:
            return []
        candidate_ids = [item[0] for item in ids_and_scores]
        score_by_id = dict(ids_and_scores)
        placeholders = ",".join("?" for _ in candidate_ids)
        sql = f"""
            SELECT * FROM vector_items
            WHERE index_name = ? AND index_version = ? AND active = 1
              AND faiss_id IN ({placeholders})
        """
        with self._connect() as connection:
            rows = connection.execute(
                sql,
                (index_name, index_version, *candidate_ids),
            ).fetchall()
        by_id = {int(row["faiss_id"]): row for row in rows}
        results: list[VectorCandidate] = []
        for faiss_id in candidate_ids:
            row = by_id.get(faiss_id)
            if row is None:
                continue
            results.append(
                VectorCandidate(
                    faiss_id=faiss_id,
                    rdf_uri=str(row["rdf_uri"]),
                    score=float(score_by_id[faiss_id]),
                    index_name=index_name,
                    index_version=index_version,
                    entity_type=str(row["entity_type"]),
                    graph_version=str(row["graph_version"]),
                    class_uri=row["class_uri"],
                    asset_path=row["asset_path"],
                    metadata=json.loads(row["metadata_json"]),
                )
            )
        return results

    def status(self) -> list[dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT index_name, version, dimension, item_count, graph_version,
                       embedding_model_id, embedding_revision, status, activated_at
                FROM vector_index_versions
                ORDER BY index_name, created_at DESC
                """
            ).fetchall()
        return [dict(row) for row in rows]

    @staticmethod
    def _row_to_version(row: sqlite3.Row) -> IndexVersion:
        return IndexVersion(
            index_name=str(row["index_name"]),
            version=str(row["version"]),
            file_path=Path(row["file_path"]),
            file_sha256=str(row["file_sha256"]),
            dimension=int(row["dimension"]),
            metric=str(row["metric"]),
            index_factory=str(row["index_factory"]),
            embedding_model_id=str(row["embedding_model_id"]),
            embedding_revision=str(row["embedding_revision"]),
            preprocessing_version=str(row["preprocessing_version"]),
            graph_version=str(row["graph_version"]),
            item_count=int(row["item_count"]),
            status=str(row["status"]),
        )
