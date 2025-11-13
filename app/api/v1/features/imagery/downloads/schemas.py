"""Schemas for download endpoints."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, HttpUrl


class DownloadType(str, Enum):
    """Types of downloads."""

    SINGLE = "single"
    BATCH = "batch"
    DATASET = "dataset"


class ExportFormat(str, Enum):
    """Export formats for datasets."""

    ZIP = "zip"
    TAR = "tar"
    COG = "cloud-optimized-geotiff"


class JobStatus(str, Enum):
    """Job status values."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"
    CANCELLED = "cancelled"


class DownloadRequest(BaseModel):
    """Request to download satellite imagery."""

    urls: List[HttpUrl] = Field(..., description="List of URLs to download")
    download_type: DownloadType = Field(
        default=DownloadType.BATCH, description="Type of download"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional metadata for the download"
    )
    priority: int = Field(
        default=5, ge=1, le=10, description="Priority (1=lowest, 10=highest)"
    )
    callback_url: Optional[HttpUrl] = Field(
        default=None, description="URL to call when download completes"
    )


class ProcessingRequest(BaseModel):
    """Request to process downloaded imagery."""

    filepath: str = Field(..., description="Path to the file to process")
    operations: List[Dict[str, Any]] = Field(
        ..., description="List of processing operations to apply"
    )


class ExportRequest(BaseModel):
    """Request to export multiple files as a dataset."""

    file_paths: List[str] = Field(..., description="List of file paths to export")
    export_format: ExportFormat = Field(..., description="Format to export files in")
    include_metadata: bool = Field(
        default=True, description="Include metadata in export"
    )


class JobResponse(BaseModel):
    """Response for job submission."""

    job_id: str = Field(..., description="Unique job identifier")
    status: JobStatus = Field(..., description="Current job status")
    created_at: datetime = Field(..., description="When the job was created")
    queue_position: Optional[int] = Field(
        default=None, description="Position in queue if pending"
    )
    estimated_time: Optional[int] = Field(
        default=None, description="Estimated time to completion in seconds"
    )
    message: str = Field(..., description="Status message")


class JobStatusResponse(BaseModel):
    """Response for job status check."""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Current status")
    progress: Optional[Dict[str, Any]] = Field(
        default=None, description="Progress information"
    )
    result: Optional[Dict[str, Any]] = Field(
        default=None, description="Job result if completed"
    )
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: Optional[datetime] = Field(
        default=None, description="When job was created"
    )
    updated_at: Optional[datetime] = Field(default=None, description="Last update time")
    completed_at: Optional[datetime] = Field(
        default=None, description="Completion time"
    )


class DownloadResult(BaseModel):
    """Result of a download operation."""

    url: str = Field(..., description="Downloaded URL")
    filepath: str = Field(..., description="Local file path")
    filename: str = Field(..., description="File name")
    size: int = Field(..., description="File size in bytes")
    hash: str = Field(..., description="SHA256 hash of file")
    downloaded_at: datetime = Field(..., description="Download timestamp")


class BatchDownloadResult(BaseModel):
    """Result of a batch download operation."""

    job_id: str = Field(..., description="Job identifier")
    status: JobStatus = Field(..., description="Overall status")
    results: List[DownloadResult] = Field(..., description="Successful downloads")
    errors: List[Dict[str, str]] = Field(default=[], description="Failed downloads")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class JobListResponse(BaseModel):
    """Response for listing jobs."""

    jobs: List[JobStatusResponse] = Field(..., description="List of jobs")
    total: int = Field(..., description="Total number of jobs")
    page: int = Field(..., description="Current page")
    per_page: int = Field(..., description="Items per page")


class CancelJobRequest(BaseModel):
    """Request to cancel a job."""

    reason: Optional[str] = Field(default=None, description="Cancellation reason")
