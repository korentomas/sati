from pydantic import BaseModel
from typing import List, Dict


class Layer(BaseModel):
    """Represents a data layer."""

    id: str
    name: str
    data: Dict


class MapView(BaseModel):
    """Represents a map view."""

    layers: List[Layer]
    base_map: str


class MetricsReport(BaseModel):
    """Represents a metrics report."""

    metrics: List[Dict]
