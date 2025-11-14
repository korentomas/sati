"""Processing API routes."""

import asyncio
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse

from app.api.v1.features.processing.schemas import (
    ClassificationRequest,
    ProcessingJob,
    ProcessingJobStatus,
    ProcessingRequest,
    ProcessingType,
    SpectralIndexRequest,
    ZonalStatisticsRequest,
)
from app.api.v1.features.processing.service import processing_service
from app.api.v1.shared.auth.deps import get_current_user

router = APIRouter(prefix="/processing", tags=["processing"])


@router.post("/jobs", response_model=ProcessingJob)
async def create_processing_job(
    request: ProcessingRequest, current_user=Depends(get_current_user)
) -> ProcessingJob:
    """
    Create a new processing job.

    Processing types:
    - spectral_index: Calculate NDVI, NDWI, EVI, etc.
    - classification: Perform image classification
    - change_detection: Detect changes between scenes
    - zonal_statistics: Calculate statistics for zones
    - temporal_composite: Create temporal composites
    - band_math: Custom band calculations
    - mask_extraction: Extract masks (cloud, water, etc.)
    """

    try:
        job = await processing_service.create_job(
            request=request, user_id=current_user.get("id")
        )
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/spectral-index", response_model=ProcessingJob)
async def calculate_spectral_index(
    request: SpectralIndexRequest, current_user=Depends(get_current_user)
) -> ProcessingJob:
    """
    Calculate spectral indices (NDVI, NDWI, EVI, etc.).

    Available indices:
    - NDVI: Normalized Difference Vegetation Index
    - NDWI: Normalized Difference Water Index
    - EVI: Enhanced Vegetation Index
    - SAVI: Soil Adjusted Vegetation Index
    - NDBI: Normalized Difference Built-up Index
    - BAI: Burned Area Index
    - MNDWI: Modified Normalized Difference Water Index
    - GNDVI: Green Normalized Difference Vegetation Index
    - NDSI: Normalized Difference Snow Index
    - NBR: Normalized Burn Ratio
    - CUSTOM: Custom band math expression
    """

    # Ensure type is set correctly
    request.type = ProcessingType.SPECTRAL_INDEX

    try:
        job = await processing_service.create_job(
            request=request, user_id=current_user.get("id")
        )
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/classification", response_model=ProcessingJob)
async def perform_classification(
    request: ClassificationRequest, current_user=Depends(get_current_user)
) -> ProcessingJob:
    """
    Perform image classification.

    Methods:
    - kmeans: K-means clustering
    - random_forest: Random Forest classifier
    - svm: Support Vector Machine
    - maximum_likelihood: Maximum Likelihood classifier
    - isodata: ISODATA clustering
    - threshold: Simple threshold classification
    """

    request.type = ProcessingType.CLASSIFICATION

    try:
        job = await processing_service.create_job(
            request=request, user_id=current_user.get("id")
        )
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/zonal-statistics", response_model=ProcessingJob)
async def calculate_zonal_statistics(
    request: ZonalStatisticsRequest, current_user=Depends(get_current_user)
) -> ProcessingJob:
    """
    Calculate statistics for specified zones.

    Statistics available:
    - mean, min, max, std
    - median, percentiles
    - count, sum
    """

    request.type = ProcessingType.ZONAL_STATISTICS

    try:
        job = await processing_service.create_job(
            request=request, user_id=current_user.get("id")
        )
        return job
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs", response_model=List[ProcessingJob])
async def list_processing_jobs(
    status: Optional[ProcessingJobStatus] = Query(None),
    limit: int = Query(20, ge=1, le=100),
    current_user=Depends(get_current_user),
) -> List[ProcessingJob]:
    """List processing jobs with optional status filter."""

    try:
        jobs = await processing_service.list_jobs(
            user_id=current_user.get("id"), status=status, limit=limit
        )
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=ProcessingJob)
async def get_job_status(
    job_id: str, current_user=Depends(get_current_user)
) -> ProcessingJob:
    """Get the status of a processing job."""

    job = await processing_service.get_job_status(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return job


@router.get("/jobs/{job_id}/result")
async def get_job_result(job_id: str, current_user=Depends(get_current_user)):
    """Get the result of a completed processing job."""

    result = await processing_service.get_job_result(job_id)

    if not result:
        raise HTTPException(status_code=404, detail="Job not found or not completed")

    return result


@router.delete("/jobs/{job_id}")
async def cancel_job(job_id: str, current_user=Depends(get_current_user)):
    """Cancel a pending or running processing job."""

    success = await processing_service.cancel_job(job_id)

    if not success:
        raise HTTPException(
            status_code=400, detail="Job cannot be cancelled or not found"
        )

    return {"message": "Job cancelled successfully"}


@router.get("/jobs/{job_id}/download")
async def download_result(
    job_id: str,
    file_index: int = Query(0, description="Index of file to download"),
    token: Optional[str] = Query(None, description="Auth token for download"),
):
    """Download processing result files."""

    # Validate token if provided (for direct download links)
    if token:
        from app.api.v1.shared.auth.jwt import verify_token

        try:
            payload = verify_token(token)
            if not payload:
                raise HTTPException(status_code=403, detail="Invalid or expired token")
        except Exception:
            raise HTTPException(status_code=403, detail="Invalid or expired token")
    else:
        raise HTTPException(status_code=403, detail="Token required for download")

    job = await processing_service.get_job_status(job_id)

    if not job or job.status != ProcessingJobStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Job not found or not completed")

    if not job.output_files or file_index >= len(job.output_files):
        raise HTTPException(status_code=404, detail="Output file not found")

    file_path = job.output_files[file_index]

    # Check if file exists
    import os

    if not os.path.exists(file_path):
        # Try with /app prefix for Docker
        file_path = f"/app/{file_path}"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Output file not found on disk")

    # Return file
    return FileResponse(
        file_path,
        media_type="application/octet-stream",
        filename=f"ndvi_{job_id}.tif",
    )


@router.get("/jobs/{job_id}/tiles/{z}/{x}/{y}.png")
async def get_result_tile(
    job_id: str,
    z: int,
    x: int,
    y: int,
    colormap: str = Query("RdYlGn", description="Color map to use"),
):
    """Generate tiles for processing results."""
    import io
    import os

    import numpy as np
    from PIL import Image
    from rio_tiler.io import Reader

    # Get job status
    job = await processing_service.get_job_status(job_id)

    if not job or job.status != ProcessingJobStatus.COMPLETED:
        raise HTTPException(status_code=404, detail="Job not found or not completed")

    if not job.output_files or len(job.output_files) == 0:
        raise HTTPException(status_code=404, detail="No output files")

    file_path = job.output_files[0]

    # Check if file exists
    if not os.path.exists(file_path):
        file_path = f"/app/{file_path}"
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="Output file not found")

    try:
        # Use rio-tiler for reading tiles from GeoTIFF

        try:
            # Open the result GeoTIFF with rio-tiler
            with Reader(file_path) as cog:
                # Read tile directly, ensuring Web Mercator projection
                # Rio-tiler automatically reprojects to Web Mercator
                # (EPSG:3857) for web tiles
                img = cog.tile(x, y, z, tilesize=256)
                data = img.data[0]  # Get first band (NDVI)
        except Exception as e:
            # If tile is outside bounds, return transparent tile
            error_str = str(e).lower()
            if "outside bounds" in error_str or "is outside" in error_str:
                transparent = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                buf = io.BytesIO()
                transparent.save(buf, format="PNG")
                buf.seek(0)
                return Response(
                    content=buf.getvalue(),
                    media_type="image/png",
                    headers={"Cache-Control": "public, max-age=3600"},
                )
            raise e

        # Get NDVI value range from job statistics
        vmin = job.result_data.get("statistics", {}).get("min", -1)
        vmax = job.result_data.get("statistics", {}).get("max", 1)

        # Rescale NDVI values to 0-255 for visualization
        # The data from rio-tiler is already in the original NDVI range
        if vmax > vmin:
            normalized = (data - vmin) / (vmax - vmin)
            normalized = np.clip(normalized * 255, 0, 255).astype(np.uint8)
        else:
            # Fallback if statistics are invalid
            normalized = np.clip((data + 1) * 127.5, 0, 255).astype(np.uint8)

        # Apply colormap without matplotlib
        # Create a simple Red-Yellow-Green colormap for NDVI
        if colormap.lower() in ["rdylgn", "rylgn"]:
            # Create RGB channels for Red-Yellow-Green colormap
            r = np.where(normalized < 128, 255, 255 - (normalized - 128) * 2)
            g = np.where(normalized < 128, normalized * 2, 255)
            b = np.zeros_like(normalized)

            rgb = np.stack([r, g, b], axis=-1).astype(np.uint8)
        else:
            # Default grayscale
            rgb = np.stack([normalized, normalized, normalized], axis=-1).astype(
                np.uint8
            )

        # Create PIL image
        img = Image.fromarray(rgb)

        # Save to bytes
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)

        return Response(
            content=buf.getvalue(),
            media_type="image/png",
            headers={
                "Cache-Control": "public, max-age=3600",
            },
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/jobs/{job_id}/updates")
async def job_updates_websocket(websocket: WebSocket, job_id: str):
    """WebSocket endpoint for real-time job status updates."""

    await websocket.accept()

    try:
        while True:
            # Get current job status
            job = await processing_service.get_job_status(job_id)

            if job:
                # Send update to client
                await websocket.send_json(
                    {
                        "job_id": job.job_id,
                        "status": job.status,
                        "progress": job.progress,
                        "stage": job.stage,
                        "message": job.message,
                    }
                )

                # Stop if job is complete
                if job.status in [
                    ProcessingJobStatus.COMPLETED,
                    ProcessingJobStatus.FAILED,
                    ProcessingJobStatus.CANCELLED,
                ]:
                    break

            # Wait before next update
            await asyncio.sleep(1)

    except WebSocketDisconnect:
        pass
    finally:
        await websocket.close()
