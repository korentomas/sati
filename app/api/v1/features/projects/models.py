from typing import Any, Dict, List

from pydantic import BaseModel, Field


class Layer(BaseModel):
    """Represents a data layer matching UML specification."""

    id: str
    name: str
    type: str = Field(
        default="raster",
        description="Type: raster, vector, index, composite, processed",
    )
    crs: str = Field(default="EPSG:4326", description="Coordinate Reference System")
    visible: bool = Field(default=True, description="Layer visibility")
    opacity: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Layer opacity (0-1)"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional layer metadata"
    )
    data: Dict = Field(
        default_factory=dict, description="Layer data (backward compatibility)"
    )


class MapView(BaseModel):
    """Represents a map view matching UML specification."""

    layers: List[Layer] = Field(description="List of layers in the view")
    base_map: str = Field(default="OpenStreetMap", description="Base map provider")


class MetricsReport(BaseModel):
    """Represents a metrics report matching UML specification."""

    avg_response_time: float = Field(
        default=0.0, description="Average response time in ms"
    )
    total_requests: int = Field(default=0, description="Total number of requests")
    errors: int = Field(default=0, description="Number of errors")
    additional_metrics: Dict[str, Any] = Field(
        default_factory=dict, description="Additional custom metrics"
    )
    metrics: List[Dict] = Field(
        default_factory=list, description="Legacy metrics list (backward compatibility)"
    )
