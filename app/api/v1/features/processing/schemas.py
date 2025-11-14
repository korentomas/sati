"""Schemas for processing operations."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

from app.api.v1.features.imagery.search.schemas import GeoJSONGeometry


class ProcessingType(str, Enum):
    """Types of processing operations."""

    SPECTRAL_INDEX = "spectral_index"
    CLASSIFICATION = "classification"
    CHANGE_DETECTION = "change_detection"
    ZONAL_STATISTICS = "zonal_statistics"
    TEMPORAL_COMPOSITE = "temporal_composite"
    BAND_MATH = "band_math"
    MASK_EXTRACTION = "mask_extraction"


class AggregationMethod(str, Enum):
    """Methods for aggregating multiple scenes."""

    MEAN = "mean"
    MEDIAN = "median"
    MAX = "max"
    MIN = "min"
    STD = "std"
    FIRST = "first"  # Use first valid pixel
    LAST = "last"  # Use last valid pixel
    COUNT = "count"  # Count of valid pixels


class SpectralIndex(str, Enum):
    """Available spectral indices."""

    NDVI = "ndvi"  # Normalized Difference Vegetation Index
    NDWI = "ndwi"  # Normalized Difference Water Index
    EVI = "evi"  # Enhanced Vegetation Index
    SAVI = "savi"  # Soil Adjusted Vegetation Index
    NDBI = "ndbi"  # Normalized Difference Built-up Index
    BAI = "bai"  # Burned Area Index
    MNDWI = "mndwi"  # Modified Normalized Difference Water Index
    GNDVI = "gndvi"  # Green Normalized Difference Vegetation Index
    NDSI = "ndsi"  # Normalized Difference Snow Index
    NBR = "nbr"  # Normalized Burn Ratio
    CUSTOM = "custom"  # Custom band math expression


class ClassificationMethod(str, Enum):
    """Classification algorithms."""

    KMEANS = "kmeans"
    RANDOM_FOREST = "random_forest"
    SVM = "svm"
    MAXIMUM_LIKELIHOOD = "maximum_likelihood"
    ISODATA = "isodata"
    THRESHOLD = "threshold"


class ProcessingRequest(BaseModel):
    """General processing request."""

    type: ProcessingType = Field(..., description="Type of processing operation")

    # Input data
    scene_ids: Optional[List[str]] = Field(
        None, description="Scene IDs to process (for single scenes)"
    )
    mosaic_id: Optional[str] = Field(
        None, description="Mosaic ID to process (for mosaics)"
    )

    # Area of interest
    aoi: Optional[GeoJSONGeometry] = Field(
        None, description="Area of interest polygon for masking"
    )

    # Aggregation settings for multi-scene processing
    aggregation_method: Optional[AggregationMethod] = Field(
        AggregationMethod.MEAN,
        description="How to aggregate multiple scenes (mean, median, max, min, etc.)",
    )

    # Processing parameters (flexible based on type)
    parameters: Dict[str, Any] = Field(
        default_factory=dict, description="Processing-specific parameters"
    )

    name: Optional[str] = Field(None, description="Custom name for the processing job")


class SpectralIndexRequest(ProcessingRequest):
    """Request for spectral index calculation."""

    type: Literal[ProcessingType.SPECTRAL_INDEX] = ProcessingType.SPECTRAL_INDEX

    index_type: SpectralIndex = Field(
        ..., description="Which spectral index to calculate"
    )

    # For custom indices
    expression: Optional[str] = Field(
        None, description="Custom band math expression (e.g., '(B8-B4)/(B8+B4)')"
    )

    # Output options
    color_map: Optional[str] = Field(
        "RdYlGn", description="Color map for visualization"
    )

    value_range: Optional[List[float]] = Field(
        None, description="Min/max values for scaling"
    )


class ClassificationRequest(ProcessingRequest):
    """Request for image classification."""

    type: Literal[ProcessingType.CLASSIFICATION] = ProcessingType.CLASSIFICATION

    method: ClassificationMethod = Field(
        ..., description="Classification algorithm to use"
    )

    num_classes: int = Field(
        5, ge=2, le=50, description="Number of classes for unsupervised methods"
    )

    training_data: Optional[Dict[str, Any]] = Field(
        None, description="Training data for supervised methods"
    )


class ZonalStatisticsRequest(ProcessingRequest):
    """Request for zonal statistics calculation."""

    type: Literal[ProcessingType.ZONAL_STATISTICS] = ProcessingType.ZONAL_STATISTICS

    statistics: List[str] = Field(
        default=["mean", "min", "max", "std"], description="Statistics to calculate"
    )

    zones: List[GeoJSONGeometry] = Field(
        ..., description="Zones (polygons) to calculate statistics for"
    )

    band_names: Optional[List[str]] = Field(
        None, description="Specific bands to analyze"
    )


class ProcessingJobStatus(str, Enum):
    """Status of a processing job."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProcessingJob(BaseModel):
    """Processing job information."""

    job_id: str
    type: ProcessingType
    status: ProcessingJobStatus
    created_at: datetime
    updated_at: datetime

    # Input reference
    scene_ids: Optional[List[str]] = None
    mosaic_id: Optional[str] = None

    # Progress tracking
    progress: Optional[float] = Field(None, ge=0, le=100)
    stage: Optional[str] = None
    message: Optional[str] = None

    # Results
    result_url: Optional[str] = None
    result_data: Optional[Dict[str, Any]] = None
    output_files: Optional[List[str]] = None

    # Metadata
    parameters: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ProcessingResult(BaseModel):
    """Result of a processing operation."""

    job_id: str
    type: ProcessingType
    status: ProcessingJobStatus

    # Output files
    output_files: List[str] = Field(
        default_factory=list, description="List of output file paths"
    )

    # Statistics or metrics
    statistics: Optional[Dict[str, Any]] = None

    # Visualization options
    visualization: Optional[Dict[str, Any]] = None

    # For display
    preview_url: Optional[str] = None
    download_url: Optional[str] = None

    # Execution info
    execution_time: float
    created_at: datetime
