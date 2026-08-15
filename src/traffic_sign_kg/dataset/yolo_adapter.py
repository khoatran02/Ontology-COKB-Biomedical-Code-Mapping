from __future__ import annotations

import hashlib
import math
import struct
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from traffic_sign_kg.dataset.models import BoundingBox, NormalizedObservation
from traffic_sign_kg.mapping.catalog import SignCatalog


@dataclass(frozen=True, slots=True)
class DatasetProfile:
    image_count: int
    label_count: int
    box_count: int
    empty_label_count: int
    class_count: int


class YoloDatasetAdapter:
    """Read existing YOLO annotations; no detector is required for the semantic MVP."""

    def __init__(
        self,
        root: Path,
        catalog: SignCatalog,
        dataset_id: str = "vn-traffic-signs",
        dataset_version: str = "dataset-1.0.0",
    ) -> None:
        self.root = root
        self.catalog = catalog
        self.dataset_id = dataset_id
        self.dataset_version = dataset_version
        self.images_dir = root / "images"
        self.labels_dir = root / "labels"
        if not self.images_dir.is_dir() or not self.labels_dir.is_dir():
            raise ValueError(f"YOLO dataset requires images/ and labels/ under {root}")

    def profile(self) -> DatasetProfile:
        images = self._images()
        labels = sorted(self.labels_dir.glob("*.txt"))
        box_count = 0
        empty_count = 0
        for label in labels:
            rows = self._label_rows(label)
            box_count += len(rows)
            empty_count += int(not rows)
        return DatasetProfile(
            image_count=len(images),
            label_count=len(labels),
            box_count=box_count,
            empty_label_count=empty_count,
            class_count=len(self.catalog.entries),
        )

    def iter_observations(self, limit: int | None = None) -> Iterable[NormalizedObservation]:
        emitted = 0
        for image_path in self._images():
            label_path = self.labels_dir / f"{image_path.stem}.txt"
            if not label_path.exists():
                raise ValueError(f"missing label for image: {image_path.name}")
            width, height = image_size(image_path)
            content_hash = f"sha256:{_sha256(image_path)}"
            for region_index, row in enumerate(self._label_rows(label_path)):
                class_id, x_center, y_center, box_width, box_height = row
                entry = self.catalog.by_id(class_id)
                bbox = _to_absolute_bbox(
                    x_center,
                    y_center,
                    box_width,
                    box_height,
                    width,
                    height,
                )
                status = "Accepted" if entry.mapping_status != "NeedsReview" else "PendingReview"
                yield NormalizedObservation(
                    dataset_id=self.dataset_id,
                    dataset_version=self.dataset_version,
                    image_id=image_path.stem,
                    region_id=f"{image_path.stem}-{region_index:02d}",
                    image_path=image_path,
                    image_width=width,
                    image_height=height,
                    source_class_id=class_id,
                    raw_class_code=entry.raw_code,
                    class_uri=str(entry.class_uri),
                    bbox=bbox,
                    provenance_uri=(
                        "https://w3id.org/vn-ts-cokb/resource/dataset-run/"
                        f"{self.dataset_id}/{self.dataset_version}"
                    ),
                    confidence=1.0,
                    content_hash=content_hash,
                    assertion_status=status,
                )
                emitted += 1
                if limit is not None and emitted >= limit:
                    return

    def _images(self) -> list[Path]:
        supported = {".jpg", ".jpeg", ".png"}
        return sorted(
            path for path in self.images_dir.iterdir() if path.suffix.lower() in supported
        )

    @staticmethod
    def _label_rows(path: Path) -> list[tuple[int, float, float, float, float]]:
        rows: list[tuple[int, float, float, float, float]] = []
        for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not raw_line.strip():
                continue
            parts = raw_line.split()
            if len(parts) != 5:
                raise ValueError(f"{path}:{line_number}: expected 5 YOLO values")
            class_id = int(parts[0])
            values = tuple(float(value) for value in parts[1:])
            if any(value < 0 or value > 1 for value in values):
                raise ValueError(f"{path}:{line_number}: normalized values must be in [0, 1]")
            rows.append((class_id, *values))
        return rows


def _to_absolute_bbox(
    x_center: float,
    y_center: float,
    box_width: float,
    box_height: float,
    image_width: int,
    image_height: int,
) -> BoundingBox:
    x_min = max(0, math.floor((x_center - box_width / 2) * image_width))
    y_min = max(0, math.floor((y_center - box_height / 2) * image_height))
    x_max = min(image_width, math.ceil((x_center + box_width / 2) * image_width))
    y_max = min(image_height, math.ceil((y_center + box_height / 2) * image_height))
    return BoundingBox(x_min=x_min, y_min=y_min, x_max=x_max, y_max=y_max)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def image_size(path: Path) -> tuple[int, int]:
    """Read PNG/JPEG dimensions with the standard library."""
    with path.open("rb") as stream:
        signature = stream.read(24)
        if signature.startswith(b"\x89PNG\r\n\x1a\n"):
            width, height = struct.unpack(">II", signature[16:24])
            return width, height
        if not signature.startswith(b"\xff\xd8"):
            raise ValueError(f"unsupported image format: {path}")
        stream.seek(2)
        while True:
            marker_start = stream.read(1)
            if not marker_start:
                break
            if marker_start != b"\xff":
                continue
            marker = stream.read(1)
            while marker == b"\xff":
                marker = stream.read(1)
            if marker in {b"\xd8", b"\xd9"}:
                continue
            length_bytes = stream.read(2)
            if len(length_bytes) != 2:
                break
            length = struct.unpack(">H", length_bytes)[0]
            if marker and marker[0] in range(0xC0, 0xC4):
                payload = stream.read(5)
                height, width = struct.unpack(">HH", payload[1:5])
                return width, height
            stream.seek(length - 2, 1)
    raise ValueError(f"could not read image dimensions: {path}")
