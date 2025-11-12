"""Router for download endpoints with Arq job queuing."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from arq import ArqRedis
from fastapi import APIRouter, Depends, HTTPException, Query, status
from loguru import logger

from app.api.v1.features.imagery.downloads.schemas import (
    BatchDownloadResult,
    CancelJobRequest,
    DownloadRequest,
    ExportRequest,
    JobListResponse,
    JobResponse,
    JobStatus,
    JobStatusResponse,
    ProcessingRequest,
)
from app.api.v1.shared.auth.deps import get_current_user
from app.workers.config import get_redis_pool
from app.workers.tasks import get_job_status, update_job_status

router = APIRouter()


@router.post("/download", response_model=JobResponse)
async def queue_download(
    request: DownloadRequest,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> JobResponse:
    """Queue satellite imagery downloads for parallel processing.

    This endpoint accepts a list of URLs and queues them for download
    by background workers. Downloads are processed in parallel with
    progress tracking.

    Returns a job ID that can be used to track progress and retrieve results.
    """
    try:
        job_id = str(uuid4())
        user_id = str(current_user.get("user_id", "anonymous"))

        # Enqueue the download job
        job = await redis_pool.enqueue_job(
            "download_imagery",
            job_id=job_id,
            urls=[str(url) for url in request.urls],
            user_id=user_id,
            metadata=request.metadata,
            _queue_name="arq:downloads",
            _job_id=job_id,
            _defer_by=0,  # Start immediately
            _expires=3600,  # Expire after 1 hour
        )

        # Set initial job status
        await update_job_status(
            redis_pool,
            job_id,
            JobStatus.PENDING.value,
            {
                "user_id": user_id,
                "total_urls": len(request.urls),
                "priority": request.priority,
                "callback_url": str(request.callback_url) if request.callback_url else None,
            },
        )

        logger.info(f"Queued download job {job_id} for user {user_id}")

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            queue_position=await _get_queue_position(redis_pool, job_id),
            estimated_time=len(request.urls) * 30,  # Rough estimate: 30s per file
            message=f"Download job queued with {len(request.urls)} file(s)",
        )

    except Exception as e:
        logger.error(f"Failed to queue download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue download job",
        )


@router.post("/process", response_model=JobResponse)
async def queue_processing(
    request: ProcessingRequest,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> JobResponse:
    """Queue image processing job.

    Process downloaded satellite imagery with various operations like
    resampling, band calculations, color corrections, etc.
    """
    try:
        job_id = str(uuid4())
        user_id = str(current_user.get("user_id", "anonymous"))

        # Enqueue the processing job
        job = await redis_pool.enqueue_job(
            "process_imagery",
            job_id=job_id,
            filepath=request.filepath,
            operations=request.operations,
            user_id=user_id,
            _queue_name="arq:processing",
            _job_id=job_id,
        )

        await update_job_status(
            redis_pool,
            job_id,
            JobStatus.PENDING.value,
            {"user_id": user_id, "filepath": request.filepath},
        )

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            message=f"Processing job queued for {request.filepath}",
        )

    except Exception as e:
        logger.error(f"Failed to queue processing: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue processing job",
        )


@router.post("/export", response_model=JobResponse)
async def queue_export(
    request: ExportRequest,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> JobResponse:
    """Queue dataset export job.

    Export multiple satellite images as a compressed dataset in various formats.
    """
    try:
        job_id = str(uuid4())
        user_id = str(current_user.get("user_id", "anonymous"))

        # Enqueue the export job
        job = await redis_pool.enqueue_job(
            "export_dataset",
            job_id=job_id,
            file_paths=request.file_paths,
            export_format=request.export_format.value,
            user_id=user_id,
            _queue_name="arq:exports",
            _job_id=job_id,
        )

        await update_job_status(
            redis_pool,
            job_id,
            JobStatus.PENDING.value,
            {
                "user_id": user_id,
                "file_count": len(request.file_paths),
                "format": request.export_format.value,
            },
        )

        return JobResponse(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            message=f"Export job queued for {len(request.file_paths)} file(s)",
        )

    except Exception as e:
        logger.error(f"Failed to queue export: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to queue export job",
        )


@router.get("/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status_endpoint(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> JobStatusResponse:
    """Get the status of a specific job.

    Returns current status, progress information, and results if completed.
    """
    try:
        # Get job status from Redis
        status_data = await get_job_status(redis_pool, job_id)

        if status_data.get("status") == "not_found":
            # Try to get job info from Arq
            job_info = await redis_pool.job_info(job_id)
            if not job_info:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
                )

            # Map Arq status to our status
            arq_status = job_info.get("status", "unknown")
            status_map = {
                "queued": JobStatus.PENDING,
                "in_progress": JobStatus.IN_PROGRESS,
                "complete": JobStatus.COMPLETED,
                "failed": JobStatus.FAILED,
            }
            mapped_status = status_map.get(arq_status, JobStatus.PENDING)

            return JobStatusResponse(
                job_id=job_id,
                status=mapped_status,
                created_at=job_info.get("enqueue_time"),
            )

        # Parse timestamps
        updated_at = status_data.get("updated_at")
        if updated_at:
            updated_at = datetime.fromisoformat(updated_at)

        return JobStatusResponse(
            job_id=job_id,
            status=JobStatus(status_data.get("status", "unknown")),
            progress=status_data,
            result=status_data.get("result"),
            error=status_data.get("error"),
            updated_at=updated_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job status",
        )


@router.get("/jobs", response_model=JobListResponse)
async def list_jobs(
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
    status_filter: Optional[JobStatus] = Query(None, description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(10, ge=1, le=100, description="Items per page"),
) -> JobListResponse:
    """List all jobs for the current user.

    Returns paginated list of jobs with optional status filtering.
    """
    try:
        user_id = str(current_user.get("user_id", "anonymous"))

        # Get all job keys for the user
        pattern = f"job:status:*"
        cursor = 0
        all_jobs = []

        # Scan Redis for job keys
        while True:
            cursor, keys = await redis_pool.scan(cursor, match=pattern, count=100)
            for key in keys:
                job_data = await redis_pool.get(key)
                if job_data:
                    job_dict = eval(job_data)  # Parse JSON string
                    if job_dict.get("user_id") == user_id:
                        job_id = key.decode().split(":")[-1]
                        all_jobs.append(
                            JobStatusResponse(
                                job_id=job_id,
                                status=JobStatus(job_dict.get("status", "unknown")),
                                progress=job_dict,
                                updated_at=datetime.fromisoformat(job_dict.get("updated_at"))
                                if job_dict.get("updated_at")
                                else None,
                            )
                        )

            if cursor == 0:
                break

        # Filter by status if specified
        if status_filter:
            all_jobs = [j for j in all_jobs if j.status == status_filter]

        # Paginate
        start = (page - 1) * per_page
        end = start + per_page
        paginated_jobs = all_jobs[start:end]

        return JobListResponse(
            jobs=paginated_jobs, total=len(all_jobs), page=page, per_page=per_page
        )

    except Exception as e:
        logger.error(f"Failed to list jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list jobs",
        )


@router.post("/jobs/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: str,
    request: Optional[CancelJobRequest] = None,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> JobResponse:
    """Cancel a pending or running job.

    Only jobs that haven't completed can be cancelled.
    """
    try:
        # Check current job status
        status_data = await get_job_status(redis_pool, job_id)
        if status_data.get("status") == "not_found":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Job not found"
            )

        current_status = status_data.get("status")
        if current_status in [JobStatus.COMPLETED.value, JobStatus.FAILED.value]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel job with status: {current_status}",
            )

        # Attempt to cancel the job
        cancelled = await redis_pool.abort_job(job_id)

        if cancelled:
            # Update job status
            await update_job_status(
                redis_pool,
                job_id,
                JobStatus.CANCELLED.value,
                {
                    "cancelled_by": str(current_user.get("user_id", "anonymous")),
                    "cancelled_reason": request.reason if request else None,
                },
            )

            return JobResponse(
                job_id=job_id,
                status=JobStatus.CANCELLED,
                created_at=datetime.now(timezone.utc),
                message="Job cancelled successfully",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to cancel job"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel job",
        )


@router.get("/jobs/{job_id}/result", response_model=BatchDownloadResult)
async def get_job_result(
    job_id: str,
    current_user: dict = Depends(get_current_user),
    redis_pool: ArqRedis = Depends(get_redis_pool),
) -> BatchDownloadResult:
    """Get the result of a completed download job.

    Returns download results including file paths, sizes, and hashes.
    Only available for completed jobs.
    """
    try:
        # Get job result from Arq
        job_result = await redis_pool.job_result(job_id)

        if job_result is None:
            # Check job status
            status_data = await get_job_status(redis_pool, job_id)
            if status_data.get("status") == JobStatus.PENDING.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job is still pending",
                )
            elif status_data.get("status") == JobStatus.IN_PROGRESS.value:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Job is still in progress",
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Job result not found",
                )

        return BatchDownloadResult(**job_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get job result: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job result",
        )


# Helper functions
async def _get_queue_position(redis_pool: ArqRedis, job_id: str) -> Optional[int]:
    """Get position of job in queue."""
    try:
        # This is a simplified implementation
        # In production, you'd want more sophisticated queue tracking
        return None
    except Exception:
        return None