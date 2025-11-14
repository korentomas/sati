"""Schemas for mosaic operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.api.v1.features.imagery.search.schemas import GeoJSONGeometry


class MosaicStrategy(str, Enum):
    """Strategy for combining overlapping pixels."""

    FIRST = "first"  # Use first valid pixel
    LAST = "last"  # Use last valid pixel
    MEAN = "mean"  # Average all valid pixels
    MAX = "max"  # Maximum pixel value
    MIN = "min"  # Minimum pixel value


class MosaicRequest(BaseModel):
    """Request to create a mosaic from multiple scenes."""

    scene_ids: List[str] = Field(..., description="List of scene IDs to mosaic")
    aoi: Optional[GeoJSONGeometry] = Field(
        None, description="Area of interest to clip mosaic to"
    )
    strategy: MosaicStrategy = Field(
        MosaicStrategy.FIRST, description="Strategy for combining overlapping pixels"
    )
    bands: List[str] = Field(
        default=["B4", "B3", "B2"], description="Bands to include in mosaic"
    )
    name: Optional[str] = Field(None, description="Custom name for the mosaic")


class MosaicJobStatus(str, Enum):
    """Status of a mosaic processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MosaicJob(BaseModel):
    """Mosaic processing job information."""

    job_id: str
    status: MosaicJobStatus
    created_at: datetime
    updated_at: datetime
    scene_ids: List[str]
    progress: Optional[float] = Field(None, ge=0, le=100)
    message: Optional[str] = None
    result_url: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MosaicTileRequest(BaseModel):
    """Request for a mosaic tile."""

    mosaic_id: str
    z: int = Field(..., ge=0, le=24)
    x: int = Field(..., ge=0)
    y: int = Field(..., ge=0)
    format: str = Field("png", pattern="^(png|jpeg|webp)$")
