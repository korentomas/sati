"""Service layer for mosaic operations."""

import json
import re
from datetime import datetime, timezone
from typing import List, Optional
from uuid import uuid4

import redis.asyncio as redis
from arq import create_pool
from arq.connections import RedisSettings

from app.api.v1.features.imagery.mosaic.schemas import (
    MosaicJob,
    MosaicJobStatus,
    MosaicRequest,
)
from app.core.config import settings
from app.core.logging import logger


class MosaicService:
    """Service for creating and managing imagery mosaics."""

    def __init__(self) -> None:
        """Initialize mosaic service."""
        # Parse redis URL to get host and port
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

    async def create_mosaic(
        self,
        request: MosaicRequest,
        user_id: str,
    ) -> MosaicJob:
        """Create a mosaic from multiple scenes.

        Args:
            request: Mosaic creation request
            user_id: ID of the user creating the mosaic

        Returns:
            MosaicJob with job information
        """
        job_id = f"mosaic_{uuid4().hex}"

        try:
            # Queue the job with ARQ
            pool = await create_pool(self.redis_settings)

            await pool.enqueue_job(
                "create_imagery_mosaic",
                job_id=job_id,
                scene_ids=request.scene_ids,
                bands=request.bands,
                strategy=request.strategy.value,
                user_id=user_id,
                aoi=request.aoi.dict() if request.aoi else None,
            )

            await pool.close()

            # Create job record
            job = MosaicJob(
                job_id=job_id,
                status=MosaicJobStatus.PENDING,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                scene_ids=request.scene_ids,
                progress=0,
                message="Mosaic job queued for processing",
                metadata={
                    "bands": request.bands,
                    "strategy": request.strategy.value,
                    "name": request.name,
                },
            )

            logger.info(f"Created mosaic job {job_id} for user {user_id}")
            return job

        except Exception as e:
            logger.error(f"Failed to create mosaic job: {e}")
            raise

    async def get_job_status(self, job_id: str) -> Optional[MosaicJob]:
        """Get the status of a mosaic job.

        Args:
            job_id: Job identifier

        Returns:
            MosaicJob with current status or None if not found
        """
        try:
            # Use direct Redis client for accessing job status
            redis_client = await redis.from_url(f"{settings.redis_url}/0")

            # Get job status from Redis
            key = f"job:status:{job_id}"
            value = await redis_client.get(key)

            await redis_client.close()

            if not value:
                return None

            status_data = json.loads(value)

            # Map Redis status to schema
            job = MosaicJob(
                job_id=job_id,
                status=MosaicJobStatus(status_data.get("status", "pending")),
                created_at=datetime.fromisoformat(
                    status_data.get(
                        "created_at", datetime.now(timezone.utc).isoformat()
                    )
                ),
                updated_at=datetime.fromisoformat(
                    status_data.get(
                        "updated_at", datetime.now(timezone.utc).isoformat()
                    )
                ),
                scene_ids=status_data.get("scene_ids", []),
                progress=status_data.get("progress", 0),
                message=status_data.get("message"),
                result_url=status_data.get("mosaic_path"),
                error=status_data.get("error"),
                metadata=status_data.get("metadata"),
            )

            return job

        except Exception as e:
            logger.error(f"Failed to get job status for {job_id}: {e}")
            return None

    async def list_user_jobs(
        self,
        user_id: str,
        limit: int = 10,
    ) -> List[MosaicJob]:
        """List mosaic jobs for a user.

        Args:
            user_id: User identifier
            limit: Maximum number of jobs to return

        Returns:
            List of MosaicJob objects
        """
        # In a production system, this would query a database
        # For now, return empty list
        return []

    async def cancel_job(self, job_id: str, user_id: str) -> bool:
        """Cancel a pending mosaic job.

        Args:
            job_id: Job identifier
            user_id: User identifier (for authorization)

        Returns:
            True if cancelled, False otherwise
        """
        try:
            # Use direct Redis client for accessing job status
            redis_client = await redis.from_url(f"{settings.redis_url}/0")

            # In ARQ, we can't directly cancel jobs, but we can mark them
            key = f"job:status:{job_id}"

            await redis_client.set(
                key,
                json.dumps(
                    {
                        "status": "cancelled",
                        "updated_at": datetime.now(timezone.utc).isoformat(),
                        "message": "Job cancelled by user",
                    }
                ),
                ex=3600,
            )

            await redis_client.close()
            return True

        except Exception as e:
            logger.error(f"Failed to cancel job {job_id}: {e}")
            return False
