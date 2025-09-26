"""Schemas for imagery search endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class GeoJSONGeometry(BaseModel):
    """GeoJSON Geometry object."""

    type: str  # Polygon, Point, etc.
    coordinates: List[Any]


class SearchRequest(BaseModel):
    """Request model for imagery search."""

    geometry: Optional[GeoJSONGeometry] = None
    bbox: Optional[List[float]] = Field(
        None,
        description="Bounding box [west, south, east, north]",
        min_items=4,
        max_items=4,
    )
    date_from: datetime
    date_to: datetime
    collections: List[str] = Field(
        default=["sentinel-2-l2a"],
        description="Collection IDs to search",
    )
    cloud_cover_max: float = Field(
        100.0,
        ge=0,
        le=100,
        description="Maximum cloud cover percentage",
    )
    limit: int = Field(20, ge=1, le=100, description="Maximum results per page")

    @validator("date_to")
    def validate_date_range(cls, v, values):
        """Ensure date_to is after date_from."""
        if "date_from" in values and v < values["date_from"]:
            raise ValueError("date_to must be after date_from")
        return v

    @property
    def datetime_range(self) -> str:
        """Format datetime range for STAC API."""
        # STAC expects ISO format with Z timezone
        date_from_str = self.date_from.strftime("%Y-%m-%dT00:00:00Z")
        date_to_str = self.date_to.strftime("%Y-%m-%dT23:59:59Z")
        return f"{date_from_str}/{date_to_str}"


class SceneProperties(BaseModel):
    """Properties of a satellite scene."""

    datetime: datetime
    cloud_cover: Optional[float] = Field(None, ge=0, le=100)
    platform: Optional[str] = None
    instrument: Optional[str] = None
    gsd: Optional[float] = Field(None, description="Ground sample distance (meters)")


class SceneResponse(BaseModel):
    """Response model for a single scene."""

    id: str
    collection: str
    bbox: List[float]
    geometry: GeoJSONGeometry
    properties: SceneProperties
    thumbnail_url: Optional[str] = None
    assets: Dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    """Response model for search results."""

    total: int = Field(0, description="Total number of results")
    returned: int = Field(0, description="Number of results in this response")
    scenes: List[SceneResponse] = Field(default_factory=list)
    next_token: Optional[str] = Field(None, description="Token for next page")


class CollectionInfo(BaseModel):
    """Information about a STAC collection."""

    id: str
    title: str
    description: Optional[str] = None
    temporal_extent: Optional[List[Optional[str]]] = None
    spatial_extent: Optional[List[float]] = None
    providers: List[str] = Field(default_factory=list)
    license: Optional[str] = None


class CollectionsResponse(BaseModel):
    """Response model for collections list."""

    collections: List[CollectionInfo] = Field(default_factory=list)