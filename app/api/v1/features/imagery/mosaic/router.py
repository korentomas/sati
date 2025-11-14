"""Router for mosaic endpoints."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.v1.features.imagery.mosaic.schemas import MosaicJob, MosaicRequest
from app.api.v1.features.imagery.mosaic.service import MosaicService
from app.api.v1.shared.auth.deps import get_current_user
from app.api.v1.shared.db.models import User
from app.core.logging import logger

router = APIRouter(prefix="/mosaic", tags=["mosaic"])


@router.post("/create", response_model=MosaicJob)
async def create_mosaic(
    request: MosaicRequest,
    current_user: User = Depends(get_current_user),
) -> MosaicJob:
    """Create a mosaic from multiple satellite scenes.

    This endpoint queues a background job to process the mosaic.
    Use the job_id to check status and retrieve results.
    """
    try:
        service = MosaicService()
        job = await service.create_mosaic(request, str(current_user.id))
        return job
    except Exception as e:
        logger.error(f"Failed to create mosaic: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create mosaic job",
        )


@router.get("/job/{job_id}", response_model=Optional[MosaicJob])
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> Optional[MosaicJob]:
    """Get the status of a mosaic processing job."""
    service = MosaicService()
    job = await service.get_job_status(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Job {job_id} not found"
        )

    return job


@router.delete("/job/{job_id}")
async def cancel_job(
    job_id: str,
    current_user: User = Depends(get_current_user),
) -> dict:
    """Cancel a pending mosaic job."""
    service = MosaicService()
    cancelled = await service.cancel_job(job_id, str(current_user.id))

    if not cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to cancel job"
        )

    return {"message": f"Job {job_id} cancelled"}


@router.get("/jobs", response_model=list[MosaicJob])
async def list_user_jobs(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
) -> list[MosaicJob]:
    """List mosaic jobs for the current user."""
    service = MosaicService()
    jobs = await service.list_user_jobs(str(current_user.id), limit)
    return jobs
