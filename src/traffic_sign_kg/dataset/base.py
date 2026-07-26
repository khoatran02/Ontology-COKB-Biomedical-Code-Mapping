from collections.abc import Iterable
from typing import Protocol

from traffic_sign_kg.dataset.models import NormalizedObservation


class DatasetAdapter(Protocol):
    """Boundary to implement when the dataset ingestion phase starts."""

    @property
    def dataset_id(self) -> str: ...

    def iter_observations(self) -> Iterable[NormalizedObservation]: ...
