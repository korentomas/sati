"""Service layer for processing operations."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

from app.api.v1.features.processing.schemas import (
    ClassificationRequest,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingRequest,
    ProcessingType,
    SpectralIndexRequest,
    ZonalStatisticsRequest,
)
from app.core.config import settings


class ProcessingService:
    """Service for managing processing operations."""

    def __init__(self):
        # Parse redis URL to get host and port
        import re

        match = re.match(r"redis://([^:]+):(\d+)", settings.redis_url)
        if match:
            host = match.group(1)
            port = int(match.group(2))
        else:
            host = "localhost"
            port = 6379

        self.redis_settings = RedisSettings(
            host=host,
            port=port,
            database=0,
        )

    async def create_job(
        self, request: ProcessingRequest, user_id: Optional[str] = None
    ) -> ProcessingJob:
        """Create and queue a processing job."""

        # Generate job ID
        job_id = str(uuid.uuid4())

        # Create job record
        job = ProcessingJob(
            job_id=job_id,
            type=request.type,
            status=ProcessingJobStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            scene_ids=request.scene_ids,
            mosaic_id=request.mosaic_id,
            parameters=request.parameters,
            progress=0,
            stage="Queued for processing",
        )

        # Store job in Redis for tracking
        redis_client = await redis.from_url(f"{settings.redis_url}/0")

        await redis_client.setex(
            f"processing_job:{job_id}", 86400, job.model_dump_json()  # 24 hour TTL
        )

        # Queue the appropriate task
        pool = await create_pool(self.redis_settings)

        try:
            # Route to appropriate task based on processing type
            if request.type == ProcessingType.SPECTRAL_INDEX:
                spec_request = SpectralIndexRequest(**request.model_dump())
                await pool.enqueue_job(
                    "calculate_spectral_index",
                    job_id=job_id,
                    index_type=spec_request.index_type.value,
                    scene_ids=spec_request.scene_ids,
                    mosaic_id=spec_request.mosaic_id,
                    aoi=spec_request.aoi.model_dump() if spec_request.aoi else None,
                    expression=spec_request.expression,
                    parameters={
                        "color_map": spec_request.color_map,
                        "value_range": spec_request.value_range,
                        **spec_request.parameters,
                    },
                    user_id=user_id,
                    aggregation_method=(
                        request.aggregation_method.value
                        if request.aggregation_method
                        else "mean"
                    ),
                )

            elif request.type == ProcessingType.CLASSIFICATION:
                class_request = ClassificationRequest(**request.model_dump())
                await pool.enqueue_job(
                    "perform_classification",
                    job_id=job_id,
                    method=class_request.method.value,
                    num_classes=class_request.num_classes,
                    scene_ids=class_request.scene_ids,
                    mosaic_id=class_request.mosaic_id,
                    aoi=class_request.aoi.model_dump() if class_request.aoi else None,
                    training_data=class_request.training_data,
                    parameters=class_request.parameters,
                    user_id=user_id,
                )

            elif request.type == ProcessingType.ZONAL_STATISTICS:
                stats_request = ZonalStatisticsRequest(**request.model_dump())
                await pool.enqueue_job(
                    "calculate_zonal_statistics",
                    job_id=job_id,
                    statistics=stats_request.statistics,
                    zones=[z.model_dump() for z in stats_request.zones],
                    scene_ids=stats_request.scene_ids,
                    mosaic_id=stats_request.mosaic_id,
                    band_names=stats_request.band_names,
                    parameters=stats_request.parameters,
                    user_id=user_id,
                )

            elif request.type == ProcessingType.CHANGE_DETECTION:
                await pool.enqueue_job(
                    "detect_changes",
                    job_id=job_id,
                    scene_ids=request.scene_ids,
                    parameters=request.parameters,
                    aoi=request.aoi.model_dump() if request.aoi else None,
                    user_id=user_id,
                )

            elif request.type == ProcessingType.TEMPORAL_COMPOSITE:
                await pool.enqueue_job(
                    "create_temporal_composite",
                    job_id=job_id,
                    scene_ids=request.scene_ids,
                    parameters=request.parameters,
                    aoi=request.aoi.model_dump() if request.aoi else None,
                    user_id=user_id,
                )

            elif request.type == ProcessingType.BAND_MATH:
                await pool.enqueue_job(
                    "calculate_band_math",
                    job_id=job_id,
                    expression=request.parameters.get("expression"),
                    scene_ids=request.scene_ids,
                    mosaic_id=request.mosaic_id,
                    aoi=request.aoi.model_dump() if request.aoi else None,
                    parameters=request.parameters,
                    user_id=user_id,
                )

            elif request.type == ProcessingType.MASK_EXTRACTION:
                await pool.enqueue_job(
                    "extract_mask",
                    job_id=job_id,
                    mask_type=request.parameters.get("mask_type", "cloud"),
                    scene_ids=request.scene_ids,
                    mosaic_id=request.mosaic_id,
                    aoi=request.aoi.model_dump() if request.aoi else None,
                    parameters=request.parameters,
                    user_id=user_id,
                )

            else:
                raise ValueError(f"Unsupported processing type: {request.type}")

        finally:
            await pool.close()
            await redis_client.close()

        return job

    async def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get the current status of a processing job."""

        redis_client = await redis.from_url(f"{settings.redis_url}/0")

        try:
            job_data = await redis_client.get(f"processing_job:{job_id}")
            if job_data:
                return ProcessingJob.model_validate_json(job_data)
            return None
        finally:
            await redis_client.close()

    async def list_jobs(
        self,
        user_id: Optional[str] = None,
        status: Optional[ProcessingJobStatus] = None,
        limit: int = 20,
    ) -> List[ProcessingJob]:
        """List processing jobs with optional filters."""

        redis_client = await redis.from_url(f"{settings.redis_url}/0")

        try:
            # Get all job keys
            pattern = "processing_job:*"
            keys = await redis_client.keys(pattern)

            jobs = []
            for key in keys[:limit]:  # Limit results
                job_data = await redis_client.get(key)
                if job_data:
                    job = ProcessingJob.model_validate_json(job_data)

                    # Apply filters
                    if status and job.status != status:
                        continue

                    jobs.append(job)

            # Sort by created_at descending
            jobs.sort(key=lambda x: x.created_at, reverse=True)

            return jobs

        finally:
            await redis_client.close()

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a processing job."""

        redis_client = await redis.from_url(f"{settings.redis_url}/0")

        try:
            # Get current job
            job_data = await redis_client.get(f"processing_job:{job_id}")
            if not job_data:
                return False

            job = ProcessingJob.model_validate_json(job_data)

            # Only cancel if pending or processing
            if job.status in [
                ProcessingJobStatus.PENDING,
                ProcessingJobStatus.PROCESSING,
            ]:
                job.status = ProcessingJobStatus.CANCELLED
                job.updated_at = datetime.utcnow()
                job.message = "Job cancelled by user"

                # Update in Redis
                await redis_client.setex(
                    f"processing_job:{job_id}", 86400, job.model_dump_json()
                )

                # TODO: Actually cancel the ARQ job if it's running
                # This would require storing the ARQ job ID and using pool.abort_job()

                return True

            return False

        finally:
            await redis_client.close()

    async def get_job_result(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get the result of a completed job."""

        job = await self.get_job_status(job_id)

        if not job or job.status != ProcessingJobStatus.COMPLETED:
            return None

        # Return result data
        return {
            "job_id": job.job_id,
            "type": job.type,
            "status": job.status,
            "result_url": job.result_url,
            "result_data": job.result_data,
            "output_files": job.output_files,
            "execution_time": job.execution_time,
            "created_at": job.created_at.isoformat(),
        }

    async def update_job_progress(
        self,
        job_id: str,
        progress: float,
        stage: Optional[str] = None,
        message: Optional[str] = None,
    ):
        """Update job progress (called by workers)."""

        redis_client = await redis.from_url(f"{settings.redis_url}/0")

        try:
            job_data = await redis_client.get(f"processing_job:{job_id}")
            if job_data:
                job = ProcessingJob.model_validate_json(job_data)

                job.progress = progress
                job.updated_at = datetime.utcnow()

                if stage:
                    job.stage = stage
                if message:
                    job.message = message

                # Update status if needed
                if progress > 0 and job.status == ProcessingJobStatus.PENDING:
                    job.status = ProcessingJobStatus.PROCESSING

                # Save back to Redis
                await redis_client.setex(
                    f"processing_job:{job_id}", 86400, job.model_dump_json()
                )

        finally:
            await redis_client.close()


# Singleton instance
processing_service = ProcessingService()
