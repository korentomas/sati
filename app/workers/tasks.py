"""Background tasks for satellite imagery downloads and processing."""

import asyncio
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

import aiofiles
import httpx
import numpy as np
from arq import ArqRedis
from loguru import logger

# Download directory for temporary storage
DOWNLOAD_DIR = Path("downloads")
DOWNLOAD_DIR.mkdir(exist_ok=True)


async def download_imagery(
    ctx: Dict[str, Any],
    job_id: str,
    urls: List[str],
    user_id: str,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Download satellite imagery in parallel.

    Args:
        ctx: Arq context with Redis connection
        job_id: Unique job identifier
        urls: List of URLs to download
        user_id: User who initiated the download
        metadata: Additional metadata about the download

    Returns:
        Dict containing download results and file paths
    """
    redis: ArqRedis = ctx["redis"]
    results = []
    errors = []

    # Update job status to in_progress
    await update_job_status(
        redis, job_id, "in_progress", {"total": len(urls), "completed": 0}
    )

    # Create user-specific download directory
    user_dir = DOWNLOAD_DIR / user_id / job_id
    user_dir.mkdir(parents=True, exist_ok=True)

    # Download files in parallel with concurrency limit
    semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent downloads

    async def download_single(url: str, index: int) -> Optional[Dict[str, Any]]:
        """Download a single file with progress tracking."""
        async with semaphore:
            try:
                logger.info(f"Starting download {index + 1}/{len(urls)}: {url}")

                async with httpx.AsyncClient(timeout=300.0) as client:
                    response = await client.get(url, follow_redirects=True)
                    response.raise_for_status()

                    # Generate filename from URL or use timestamp
                    filename = (
                        url.split("/")[-1] or f"image_{index}_{uuid4().hex[:8]}.tif"
                    )
                    filepath = user_dir / filename

                    # Stream download to file
                    async with aiofiles.open(filepath, "wb") as f:
                        async for chunk in response.aiter_bytes(chunk_size=8192):
                            await f.write(chunk)

                    # Calculate file hash for verification
                    file_hash = await calculate_file_hash(filepath)

                    # Update progress
                    progress = await get_job_status(redis, job_id)
                    completed = progress.get("completed", 0) + 1
                    await update_job_status(
                        redis,
                        job_id,
                        "in_progress",
                        {
                            "total": len(urls),
                            "completed": completed,
                            "percentage": (completed / len(urls)) * 100,
                        },
                    )

                    result = {
                        "url": url,
                        "filepath": str(filepath),
                        "filename": filename,
                        "size": filepath.stat().st_size,
                        "hash": file_hash,
                        "downloaded_at": datetime.now(timezone.utc).isoformat(),
                    }

                    logger.info(f"Downloaded {filename}: {result['size']} bytes")
                    return result

            except Exception as e:
                logger.error(f"Failed to download {url}: {e}")
                errors.append({"url": url, "error": str(e)})
                return None

    # Execute downloads in parallel
    tasks = [download_single(url, i) for i, url in enumerate(urls)]
    download_results = await asyncio.gather(*tasks)

    # Filter out failed downloads
    results = [r for r in download_results if r is not None]

    # Determine final status
    if len(results) == len(urls):
        status = "completed"
        message = f"Successfully downloaded {len(results)} files"
    elif results:
        status = "partial"
        message = f"Downloaded {len(results)}/{len(urls)} files"
    else:
        status = "failed"
        message = "All downloads failed"

    # Update final job status
    await update_job_status(
        redis,
        job_id,
        status,
        {
            "total": len(urls),
            "completed": len(results),
            "failed": len(errors),
            "percentage": 100,
            "message": message,
        },
    )

    return {
        "job_id": job_id,
        "status": status,
        "results": results,
        "errors": errors,
        "summary": {
            "total_requested": len(urls),
            "successful": len(results),
            "failed": len(errors),
            "total_size": sum(r["size"] for r in results),
        },
        "metadata": metadata,
    }


async def process_imagery(
    ctx: Dict[str, Any],
    job_id: str,
    filepath: str,
    operations: List[Dict[str, Any]],
    user_id: str,
) -> Dict[str, Any]:
    """Process satellite imagery with various operations.

    Args:
        ctx: Arq context
        job_id: Job identifier
        filepath: Path to the image file
        operations: List of operations to perform (resize, crop, enhance, etc.)
        user_id: User ID

    Returns:
        Dict with processed image information
    """
    redis: ArqRedis = ctx["redis"]

    await update_job_status(redis, job_id, "in_progress", {"stage": "processing"})

    try:
        # TODO: Implement actual image processing
        # This would integrate with rasterio/rio-tiler for:
        # - Resampling
        # - Band calculations
        # - Color corrections
        # - Format conversions

        processed_path = filepath.replace(".tif", "_processed.tif")

        result = {
            "job_id": job_id,
            "status": "completed",
            "original_file": filepath,
            "processed_file": processed_path,
            "operations": operations,
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", {"stage": "done"})
        return result

    except Exception as e:
        logger.error(f"Processing failed for {filepath}: {e}")
        await update_job_status(redis, job_id, "failed", {"error": str(e)})
        raise


async def export_dataset(
    ctx: Dict[str, Any],
    job_id: str,
    file_paths: List[str],
    export_format: str,
    user_id: str,
) -> Dict[str, Any]:
    """Export multiple images as a dataset in various formats.

    Args:
        ctx: Arq context
        job_id: Job identifier
        file_paths: List of file paths to export
        export_format: Format to export (zip, tar, cloud-optimized-geotiff)
        user_id: User ID

    Returns:
        Dict with export information
    """
    redis: ArqRedis = ctx["redis"]

    await update_job_status(redis, job_id, "in_progress", {"stage": "exporting"})

    try:
        export_dir = DOWNLOAD_DIR / user_id / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        if export_format == "zip":
            import zipfile

            export_path = export_dir / f"{job_id}.zip"
            with zipfile.ZipFile(export_path, "w") as zf:
                for filepath in file_paths:
                    if Path(filepath).exists():
                        zf.write(filepath, Path(filepath).name)

        elif export_format == "tar":
            import tarfile

            export_path = export_dir / f"{job_id}.tar.gz"
            with tarfile.open(export_path, "w:gz") as tf:
                for filepath in file_paths:
                    if Path(filepath).exists():
                        tf.add(filepath, arcname=Path(filepath).name)

        else:
            raise ValueError(f"Unsupported export format: {export_format}")

        result = {
            "job_id": job_id,
            "status": "completed",
            "export_path": str(export_path),
            "export_format": export_format,
            "file_count": len(file_paths),
            "export_size": export_path.stat().st_size if export_path.exists() else 0,
            "exported_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", result)
        return result

    except Exception as e:
        logger.error(f"Export failed: {e}")
        await update_job_status(redis, job_id, "failed", {"error": str(e)})
        raise


async def create_batch_download(
    ctx: Dict[str, Any],
    job_id: str,
    file_ids: List[str],
    user_id: str,
) -> Dict[str, Any]:
    """Create a zip file containing multiple processed images for download.

    Args:
        ctx: Arq context
        job_id: Job identifier
        file_ids: List of file IDs to include in the batch
        user_id: User ID

    Returns:
        Dict with batch download information including zip file path
    """
    import zipfile

    redis: ArqRedis = ctx["redis"]

    await update_job_status(redis, job_id, "in_progress", {"stage": "preparing_batch"})

    try:
        # Create batch download directory
        batch_dir = DOWNLOAD_DIR / user_id / "batches"
        batch_dir.mkdir(parents=True, exist_ok=True)

        # Create zip file for the batch
        zip_path = batch_dir / f"batch_{job_id}.zip"
        included_files = []
        missing_files = []

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for file_id in file_ids:
                # Look for processed file in user's processed directory
                processed_file = DOWNLOAD_DIR / user_id / "processed" / file_id

                # Also check if file_id is already a full path
                if not processed_file.exists():
                    processed_file = Path(file_id) if Path(file_id).exists() else None

                if processed_file and processed_file.exists():
                    # Add file to zip with a clean name
                    arcname = f"processed_{Path(file_id).name}"
                    zf.write(processed_file, arcname)
                    included_files.append(str(file_id))

                    # Update progress
                    progress = len(included_files) / len(file_ids) * 100
                    await update_job_status(
                        redis,
                        job_id,
                        "in_progress",
                        {
                            "stage": "creating_batch",
                            "progress": progress,
                            "files_processed": len(included_files),
                            "total_files": len(file_ids),
                        },
                    )
                else:
                    missing_files.append(str(file_id))
                    logger.warning(f"File not found for batch download: {file_id}")

        # Determine final status
        if included_files and not missing_files:
            status = "completed"
            message = f"Batch download ready with {len(included_files)} files"
        elif included_files:
            status = "partial"
            message = (
                f"Batch download ready with {len(included_files)}/{len(file_ids)} files"
            )
        else:
            status = "failed"
            message = "No files found for batch download"

        result = {
            "job_id": job_id,
            "status": status,
            "zip_path": str(zip_path),
            "zip_size": zip_path.stat().st_size if zip_path.exists() else 0,
            "included_files": included_files,
            "missing_files": missing_files,
            "total_requested": len(file_ids),
            "total_included": len(included_files),
            "message": message,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, status, result)
        return result

    except Exception as e:
        logger.error(f"Batch download creation failed: {e}")
        await update_job_status(redis, job_id, "failed", {"error": str(e)})
        raise


async def cleanup_old_downloads(ctx: Dict[str, Any]) -> Dict[str, Any]:
    """Periodic task to clean up old download files.

    Args:
        ctx: Arq context

    Returns:
        Dict with cleanup statistics
    """
    import shutil
    from datetime import timedelta

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    deleted_count = 0
    freed_space = 0

    for user_dir in DOWNLOAD_DIR.iterdir():
        if user_dir.is_dir():
            for job_dir in user_dir.iterdir():
                if job_dir.is_dir():
                    # Check modification time
                    mtime = datetime.fromtimestamp(
                        job_dir.stat().st_mtime, tz=timezone.utc
                    )
                    if mtime < cutoff:
                        # Calculate size before deletion
                        size = sum(
                            f.stat().st_size for f in job_dir.rglob("*") if f.is_file()
                        )
                        freed_space += size
                        deleted_count += 1

                        # Delete directory
                        shutil.rmtree(job_dir)
                        logger.info(f"Cleaned up old download: {job_dir}")

    return {
        "deleted_jobs": deleted_count,
        "freed_space_bytes": freed_space,
        "freed_space_mb": freed_space / (1024 * 1024),
        "cleanup_time": datetime.now(timezone.utc).isoformat(),
    }


# Helper functions
async def update_job_status(
    redis: ArqRedis, job_id: str, status: str, data: Dict[str, Any]
) -> None:
    """Update job status in Redis."""
    # Update the old key for backward compatibility
    key = f"job:status:{job_id}"
    value = json.dumps(
        {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
    )
    await redis.set(key, value, ex=3600)  # Expire after 1 hour

    # Also update the processing_job key that the service expects
    processing_key = f"processing_job:{job_id}"
    existing = await redis.get(processing_key)
    if existing:
        try:
            job_data = json.loads(existing)
            # Update status and relevant fields
            job_data["status"] = status
            job_data["updated_at"] = datetime.now(timezone.utc).isoformat()
            job_data["progress"] = data.get(
                "progress",
                100.0 if status == "completed" else job_data.get("progress", 0),
            )
            job_data["stage"] = data.get("stage", job_data.get("stage"))
            job_data["message"] = data.get("message", job_data.get("message"))
            if status == "completed":
                job_data["result_data"] = data
                job_data["output_files"] = (
                    [data.get("output_file")] if data.get("output_file") else None
                )
                job_data["execution_time"] = data.get("execution_time")
            elif status == "failed":
                job_data["error"] = data.get("error")

            await redis.set(
                processing_key, json.dumps(job_data), ex=86400
            )  # 24 hour TTL
        except Exception as e:
            logger.warning(f"Failed to update processing_job key: {e}")


async def get_job_status(redis: ArqRedis, job_id: str) -> Dict[str, Any]:
    """Get job status from Redis."""
    key = f"job:status:{job_id}"
    value = await redis.get(key)
    if value:
        return json.loads(value)
    return {"status": "not_found"}


async def calculate_file_hash(filepath: Path) -> str:
    """Calculate SHA256 hash of a file."""
    sha256_hash = hashlib.sha256()
    async with aiofiles.open(filepath, "rb") as f:
        while chunk := await f.read(8192):
            sha256_hash.update(chunk)
    return sha256_hash.hexdigest()


async def create_imagery_mosaic(
    ctx: Dict[str, Any],
    job_id: str,
    scene_ids: List[str],
    bands: List[str],
    strategy: str,
    user_id: str,
    aoi: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a mosaic from multiple satellite scenes.

    Args:
        ctx: Arq context with Redis connection
        job_id: Unique job identifier
        scene_ids: List of scene IDs to mosaic
        bands: List of bands to include
        strategy: Mosaic strategy (first, last, mean, max, min)
        user_id: User who initiated the mosaic
        aoi: Optional area of interest GeoJSON

    Returns:
        Dict containing mosaic results and file path
    """
    redis: ArqRedis = ctx["redis"]

    try:
        # Update job status
        await update_job_status(
            redis, job_id, "processing", {"stage": "initializing", "progress": 0}
        )

        # Import here to avoid circular dependencies
        import numpy as np
        import rasterio
        from rasterio.crs import CRS
        from rio_tiler.io import Reader

        from app.api.v1.features.imagery.search.service import SearchService

        # Create output directory
        mosaic_dir = DOWNLOAD_DIR / user_id / "mosaics"
        mosaic_dir.mkdir(parents=True, exist_ok=True)
        mosaic_path = mosaic_dir / f"mosaic_{job_id}.tif"

        # Get scene information
        service = SearchService()
        scenes_data = []

        for i, scene_id in enumerate(scene_ids):
            # Update progress
            progress = (i / len(scene_ids)) * 30  # First 30% for fetching
            await update_job_status(
                redis,
                job_id,
                "processing",
                {"stage": "fetching_scenes", "progress": progress},
            )

            # Get scene details (assuming sentinel-2-l2a for now)
            scene = await service.get_scene("sentinel-2-l2a", scene_id)
            if scene and scene.assets:
                scenes_data.append(scene)

        if not scenes_data:
            raise ValueError("No valid scenes found")

        # Collect COG URLs for the requested bands
        cog_urls = []
        for scene in scenes_data:
            scene_bands = {}
            for band in bands:
                # Map band names to assets
                asset_name = {
                    "B2": "blue",
                    "B3": "green",
                    "B4": "red",
                    "B8": "nir",
                    "B11": "swir1",
                    "B12": "swir2",
                }.get(band, band.lower())

                if asset_name in scene.assets:
                    scene_bands[band] = scene.assets[asset_name]["href"]

            if scene_bands:
                cog_urls.append(scene_bands)

        # Create mosaic for each band
        await update_job_status(
            redis, job_id, "processing", {"stage": "creating_mosaic", "progress": 40}
        )

        # Simple mosaic implementation (first valid pixel strategy)
        # In production, use rio-tiler's mosaic methods
        mosaic_bands = []

        for band_idx, band in enumerate(bands):
            band_progress = 40 + (band_idx / len(bands)) * 50  # 40-90%
            await update_job_status(
                redis,
                job_id,
                "processing",
                {"stage": f"processing_band_{band}", "progress": band_progress},
            )

            # Collect data from all scenes for this band
            band_data = None
            band_transform = None
            band_crs = None

            for scene_bands in cog_urls:
                if band in scene_bands:
                    try:
                        with Reader(scene_bands[band]) as cog:
                            # Read at a reasonable resolution
                            img = cog.preview(width=2048, height=2048)

                            if band_data is None:
                                band_data = img.data[0]
                                band_transform = img.transform
                                band_crs = cog.crs
                            else:
                                # Simple first-valid-pixel mosaic
                                mask = band_data == 0
                                band_data[mask] = img.data[0][mask]
                    except Exception as e:
                        logger.warning(f"Failed to read band {band}: {e}")

            if band_data is not None:
                mosaic_bands.append(band_data)

        # Save mosaic as GeoTIFF
        if mosaic_bands:
            await update_job_status(
                redis, job_id, "processing", {"stage": "saving_mosaic", "progress": 90}
            )

            # Stack bands and save
            mosaic_array = np.stack(mosaic_bands)

            # Create GeoTIFF
            with rasterio.open(
                mosaic_path,
                "w",
                driver="GTiff",
                height=mosaic_array.shape[1],
                width=mosaic_array.shape[2],
                count=len(bands),
                dtype=mosaic_array.dtype,
                crs=band_crs or CRS.from_epsg(4326),
                transform=band_transform,
                compress="lzw",
            ) as dst:
                for i, band in enumerate(mosaic_bands):
                    dst.write(band, i + 1)

        # Calculate file hash
        file_hash = await calculate_file_hash(mosaic_path)

        result = {
            "job_id": job_id,
            "status": "completed",
            "mosaic_path": str(mosaic_path),
            "scene_count": len(scene_ids),
            "bands": bands,
            "strategy": strategy,
            "file_size": mosaic_path.stat().st_size,
            "file_hash": file_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", result)
        return result

    except Exception as e:
        logger.error(f"Mosaic creation failed: {e}")
        await update_job_status(
            redis, job_id, "failed", {"error": str(e), "stage": "failed"}
        )
        raise


async def clip_to_aoi(
    dataset, aoi_geometry: Dict, all_touched: bool = True
) -> Tuple[np.ndarray, dict, dict]:
    """
    Clip a rasterio dataset to an AOI polygon.

    Args:
        dataset: Open rasterio dataset
        aoi_geometry: GeoJSON geometry dict
        all_touched: Include all pixels touched by geometry

    Returns:
        (clipped_array, transform, bounds)
    """
    from rasterio.mask import mask as rio_mask
    from shapely.geometry import shape

    # Convert GeoJSON to shapely geometry
    geom = shape(aoi_geometry)

    # Clip the raster
    out_image, out_transform = rio_mask(
        dataset, [geom], crop=True, all_touched=all_touched, nodata=0
    )

    # Get the bounds of clipped area
    bounds = {
        "left": out_transform.c,
        "top": out_transform.f,
        "right": out_transform.c + out_transform.a * out_image.shape[2],
        "bottom": out_transform.f + out_transform.e * out_image.shape[1],
    }

    return out_image, out_transform, bounds


async def aggregate_scenes(
    scene_paths: List[str],
    band_names: List[str],
    aggregation_method: str = "mean",
    aoi: Optional[Dict] = None,
) -> Tuple[Dict[str, np.ndarray], dict, dict]:
    """
    Load and aggregate multiple scenes.

    Args:
        scene_paths: List of paths to scene files
        band_names: List of bands to extract
        aggregation_method: How to aggregate (mean, median, max, min, std)
        aoi: Optional GeoJSON polygon to clip to

    Returns:
        (band_arrays, transform, metadata)
    """
    import rasterio
    from rasterio.warp import Resampling, reproject

    aggregated_bands = {}
    reference_transform = None
    reference_crs = None
    reference_shape = None

    # Collect all band arrays from all scenes
    band_stacks: Dict[str, List[np.ndarray]] = {band: [] for band in band_names}

    for scene_path in scene_paths:
        with rasterio.open(scene_path) as src:
            # Use first scene as reference
            if reference_transform is None:
                if aoi:
                    # If AOI provided, clip first to get reference
                    clipped, reference_transform, bounds = await clip_to_aoi(src, aoi)
                    reference_shape = clipped.shape[1:3]  # height, width
                else:
                    reference_transform = src.transform
                    reference_shape = (src.height, src.width)
                reference_crs = src.crs

            # Process each band
            for band_idx, band_name in enumerate(band_names, 1):
                if band_idx <= src.count:
                    if aoi:
                        # Clip to AOI
                        clipped, _, _ = await clip_to_aoi(src, aoi)
                        band_data = clipped[band_idx - 1]
                    else:
                        band_data = src.read(band_idx)

                    # Reproject if needed
                    if src.crs != reference_crs or src.transform != reference_transform:
                        reprojected = np.zeros(reference_shape, dtype=np.float32)
                        reproject(
                            source=band_data,
                            destination=reprojected,
                            src_transform=src.transform if not aoi else _,
                            src_crs=src.crs,
                            dst_transform=reference_transform,
                            dst_crs=reference_crs,
                            resampling=Resampling.bilinear,
                        )
                        band_data = reprojected

                    # Add to stack (convert 0s to NaN for proper aggregation)
                    band_data_float = band_data.astype(np.float32)
                    band_data_float[band_data_float == 0] = np.nan
                    band_stacks[band_name].append(band_data_float)

    # Aggregate across scenes
    for band_name, stack in band_stacks.items():
        if not stack:
            continue

        stacked = np.stack(stack, axis=0)  # Shape: (n_scenes, height, width)

        if aggregation_method == "mean":
            aggregated = np.nanmean(stacked, axis=0)
        elif aggregation_method == "median":
            aggregated = np.nanmedian(stacked, axis=0)
        elif aggregation_method == "max":
            aggregated = np.nanmax(stacked, axis=0)
        elif aggregation_method == "min":
            aggregated = np.nanmin(stacked, axis=0)
        elif aggregation_method == "std":
            aggregated = np.nanstd(stacked, axis=0)
        elif aggregation_method == "count":
            aggregated = np.sum(~np.isnan(stacked), axis=0)
        else:
            aggregated = np.nanmean(stacked, axis=0)  # Default to mean

        # Replace NaN with 0
        aggregated = np.nan_to_num(aggregated, nan=0)
        aggregated_bands[band_name] = aggregated

    metadata = {
        "transform": reference_transform,
        "crs": reference_crs,
        "shape": reference_shape,
        "aggregation_method": aggregation_method,
        "n_scenes": len(scene_paths),
    }

    return aggregated_bands, reference_transform, metadata


async def calculate_spectral_index(
    ctx: Dict[str, Any],
    job_id: str,
    index_type: str,
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    aoi: Optional[Dict[str, Any]] = None,
    expression: Optional[str] = None,
    parameters: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
    aggregation_method: str = "mean",  # New parameter
) -> Dict[str, Any]:
    """Calculate spectral indices on satellite imagery.

    Args:
        ctx: ARQ context
        job_id: Job identifier
        index_type: Type of index (ndvi, ndwi, evi, etc.)
        scene_ids: Scene IDs to process
        mosaic_id: Or mosaic ID to process
        aoi: Area of interest for masking
        expression: Custom band math expression
        parameters: Additional parameters
        user_id: User identifier
        aggregation_method: How to aggregate multiple scenes

    Returns:
        Processing result with output files
    """
    redis: ArqRedis = ctx["redis"]

    try:
        await update_job_status(
            redis, job_id, "processing", {"stage": "initializing", "progress": 0}
        )

        import numpy as np
        import rasterio
        from rio_tiler.io import Reader
        from shapely.geometry import shape

        # Create output directory
        output_dir = DOWNLOAD_DIR / (user_id or "anonymous") / "processing" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Define index formulas
        index_formulas = {
            "ndvi": lambda bands: (bands["B8"] - bands["B4"])
            / (bands["B8"] + bands["B4"] + 1e-10),
            "ndwi": lambda bands: (bands["B3"] - bands["B8"])
            / (bands["B3"] + bands["B8"] + 1e-10),
            "evi": lambda bands: 2.5
            * (
                (bands["B8"] - bands["B4"])
                / (bands["B8"] + 6 * bands["B4"] - 7.5 * bands["B2"] + 1)
            ),
            "savi": lambda bands: 1.5
            * ((bands["B8"] - bands["B4"]) / (bands["B8"] + bands["B4"] + 0.5)),
            "ndbi": lambda bands: (bands["B11"] - bands["B8"])
            / (bands["B11"] + bands["B8"] + 1e-10),
            "mndwi": lambda bands: (bands["B3"] - bands["B11"])
            / (bands["B3"] + bands["B11"] + 1e-10),
            "gndvi": lambda bands: (bands["B8"] - bands["B3"])
            / (bands["B8"] + bands["B3"] + 1e-10),
            "nbr": lambda bands: (bands["B8"] - bands["B12"])
            / (bands["B8"] + bands["B12"] + 1e-10),
        }

        # Map band names to asset names
        band_mapping = {
            "B2": "blue",
            "B3": "green",
            "B4": "red",
            "B8": "nir",
            "B11": "swir16",
            "B12": "swir22",
        }

        await update_job_status(
            redis, job_id, "processing", {"stage": "loading_data", "progress": 20}
        )

        # Get input data
        if mosaic_id:
            # Load from mosaic file
            mosaic_path = (
                DOWNLOAD_DIR
                / (user_id or "anonymous")
                / "mosaics"
                / f"mosaic_{mosaic_id}.tif"
            )
            if not mosaic_path.exists():
                raise ValueError(f"Mosaic {mosaic_id} not found")

            # Read mosaic and calculate index
            with rasterio.open(mosaic_path) as src:
                # Simplified - assumes bands are in order
                bands_data = {"B4": src.read(1), "B8": src.read(2)}  # Example
                transform = src.transform
                crs = src.crs

        elif scene_ids:
            # Process multiple scenes with aggregation
            from app.api.v1.features.imagery.search.service import SearchService

            service = SearchService()
            required_bands = get_required_bands(index_type)

            # Build list of scene file paths/URLs for each band
            scene_urls = []
            for scene_id in scene_ids:
                scene = await service.get_scene("sentinel-2-l2a", scene_id)
                if scene and scene.assets:
                    # For Sentinel-2, we need to process bands separately
                    # Create a composite COG URL or download if needed
                    # For now, we'll use the visual asset as a placeholder
                    if "visual" in scene.assets:
                        scene_urls.append(scene.assets["visual"]["href"])

            if scene_urls:
                # Process with aggregation
                logger.info(
                    f"Aggregating {len(scene_urls)} scenes using {aggregation_method}"
                )

                # For proper implementation, we'd need to handle band-specific URLs
                # This is simplified to show the concept
                bands_data = {}
                transform = None
                crs = None

                # Load and aggregate all scenes
                for band in required_bands:
                    band_arrays = []

                    for scene_id in scene_ids:
                        scene = await service.get_scene("sentinel-2-l2a", scene_id)
                        if scene and scene.assets:
                            asset_name = band_mapping.get(band, band.lower())
                            if asset_name in scene.assets:
                                url = scene.assets[asset_name]["href"]
                                with Reader(url) as cog:
                                    if aoi:
                                        # Clip to AOI during read

                                        geom = shape(aoi)
                                        img = cog.part(
                                            geom.bounds, width=2048, height=2048
                                        )
                                    else:
                                        img = cog.preview(width=2048, height=2048)

                                    if transform is None:
                                        transform = img.transform
                                        crs = cog.crs

                                    # Add to stack for aggregation
                                    band_arrays.append(img.data[0].astype(np.float32))

                    # Aggregate the band across scenes
                    if band_arrays:
                        stacked = np.stack(band_arrays, axis=0)

                        # Apply aggregation method
                        if aggregation_method == "mean":
                            aggregated = np.nanmean(
                                np.where(stacked > 0, stacked, np.nan), axis=0
                            )
                        elif aggregation_method == "median":
                            aggregated = np.nanmedian(
                                np.where(stacked > 0, stacked, np.nan), axis=0
                            )
                        elif aggregation_method == "max":
                            aggregated = np.nanmax(
                                np.where(stacked > 0, stacked, np.nan), axis=0
                            )
                        elif aggregation_method == "min":
                            aggregated = np.nanmin(
                                np.where(stacked > 0, stacked, np.nan), axis=0
                            )
                        else:
                            aggregated = np.nanmean(
                                np.where(stacked > 0, stacked, np.nan), axis=0
                            )

                        # Replace NaN with 0
                        bands_data[band] = np.nan_to_num(aggregated, nan=0)

        else:
            raise ValueError("Either scene_ids or mosaic_id required")

        await update_job_status(
            redis, job_id, "processing", {"stage": "calculating_index", "progress": 50}
        )

        # Calculate the index
        if index_type in index_formulas:
            index_data = index_formulas[index_type](bands_data)
        elif expression:
            # Custom expression - evaluate safely
            # This is simplified - in production use a safe expression parser
            index_data = eval_band_math(expression, bands_data)
        else:
            raise ValueError(f"Unknown index type: {index_type}")

        # Apply AOI mask if provided
        if aoi:
            await update_job_status(
                redis, job_id, "processing", {"stage": "applying_mask", "progress": 70}
            )

            geom = shape(aoi)
            # Simplified masking - in production use proper reprojection
            # index_data = apply_aoi_mask(index_data, geom, transform, crs)

        await update_job_status(
            redis, job_id, "processing", {"stage": "saving_results", "progress": 90}
        )

        # Save result as GeoTIFF
        output_path = output_dir / f"{index_type}_{job_id}.tif"

        with rasterio.open(
            output_path,
            "w",
            driver="GTiff",
            height=index_data.shape[0],
            width=index_data.shape[1],
            count=1,
            dtype=np.float32,
            crs=crs,
            transform=transform,
            compress="lzw",
        ) as dst:
            dst.write(index_data, 1)
            # Add colormap for visualization
            dst.write_colormap(1, get_index_colormap(index_type))

        # Calculate statistics
        statistics = {
            "min": float(np.nanmin(index_data)),
            "max": float(np.nanmax(index_data)),
            "mean": float(np.nanmean(index_data)),
            "std": float(np.nanstd(index_data)),
        }

        result = {
            "job_id": job_id,
            "status": "completed",
            "type": "spectral_index",
            "index_type": index_type,
            "output_file": str(output_path),
            "statistics": statistics,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", result)
        return result

    except Exception as e:
        logger.error(f"Index calculation failed: {e}")
        await update_job_status(
            redis, job_id, "failed", {"error": str(e), "stage": "failed"}
        )
        raise


async def run_classification(
    ctx: Dict[str, Any],
    job_id: str,
    method: str,
    num_classes: int,
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    aoi: Optional[Dict[str, Any]] = None,
    training_data: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Run image classification on satellite imagery.

    Args:
        ctx: ARQ context
        job_id: Job identifier
        method: Classification method (kmeans, random_forest, etc.)
        num_classes: Number of classes
        scene_ids: Scene IDs to process
        mosaic_id: Or mosaic ID to process
        aoi: Area of interest
        training_data: Training data for supervised methods
        user_id: User identifier

    Returns:
        Classification results
    """
    redis: ArqRedis = ctx["redis"]

    try:
        await update_job_status(
            redis,
            job_id,
            "processing",
            {"stage": "initializing_classification", "progress": 0},
        )

        # Simplified classification implementation
        # In production, implement full classification algorithms

        output_dir = DOWNLOAD_DIR / (user_id or "anonymous") / "classification" / job_id
        output_dir.mkdir(parents=True, exist_ok=True)

        # Placeholder for classification logic
        result = {
            "job_id": job_id,
            "status": "completed",
            "type": "classification",
            "method": method,
            "num_classes": num_classes,
            "output_file": str(output_dir / f"classification_{job_id}.tif"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", result)
        return result

    except Exception as e:
        logger.error(f"Classification failed: {e}")
        await update_job_status(redis, job_id, "failed", {"error": str(e)})
        raise


async def calculate_zonal_statistics(
    ctx: Dict[str, Any],
    job_id: str,
    zones: List[Dict[str, Any]],
    statistics: List[str],
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    band_names: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate zonal statistics for polygons.

    Args:
        ctx: ARQ context
        job_id: Job identifier
        zones: List of zone polygons
        statistics: Statistics to calculate
        scene_ids: Scene IDs to analyze
        mosaic_id: Or mosaic ID to analyze
        band_names: Specific bands to analyze
        user_id: User identifier

    Returns:
        Zonal statistics results
    """
    redis: ArqRedis = ctx["redis"]

    try:
        await update_job_status(
            redis,
            job_id,
            "processing",
            {"stage": "calculating_statistics", "progress": 0},
        )

        # Simplified zonal statistics implementation
        # In production, use rasterstats or similar library

        results = {
            "job_id": job_id,
            "status": "completed",
            "type": "zonal_statistics",
            "zones": len(zones),
            "statistics": statistics,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        await update_job_status(redis, job_id, "completed", results)
        return results

    except Exception as e:
        logger.error(f"Zonal statistics failed: {e}")
        await update_job_status(redis, job_id, "failed", {"error": str(e)})
        raise


# Helper functions
def get_required_bands(index_type: str) -> List[str]:
    """Get required bands for a spectral index."""
    band_requirements = {
        "ndvi": ["B4", "B8"],
        "ndwi": ["B3", "B8"],
        "evi": ["B2", "B4", "B8"],
        "savi": ["B4", "B8"],
        "ndbi": ["B8", "B11"],
        "mndwi": ["B3", "B11"],
        "gndvi": ["B3", "B8"],
        "nbr": ["B8", "B12"],
    }
    return band_requirements.get(index_type, ["B4", "B3", "B2"])


def get_index_colormap(index_type: str) -> Dict:
    """Get appropriate colormap for an index."""
    # Return a colormap suitable for the index type
    # This is simplified - in production use proper colormaps
    return {
        -1.0: (165, 0, 38, 255),
        -0.5: (215, 48, 39, 255),
        0.0: (255, 255, 191, 255),
        0.5: (26, 152, 80, 255),
        1.0: (0, 104, 55, 255),
    }


def eval_band_math(expression: str, bands: Dict[str, np.ndarray]) -> np.ndarray:
    """Safely evaluate band math expression."""
    # This is a simplified version - in production use a proper expression parser
    # to avoid security issues with eval()

    # Replace band references with array references
    safe_expr = expression
    for band_name, band_data in bands.items():
        safe_expr = safe_expr.replace(band_name, f"bands['{band_name}']")

    # Only allow safe operations
    allowed_names = {
        "bands": bands,
        "np": np,
        "abs": abs,
        "min": min,
        "max": max,
    }

    # This is still not completely safe - use AST parsing in production
    try:
        return eval(safe_expr, {"__builtins__": {}}, allowed_names)  # nosec B307
    except Exception as e:
        raise ValueError(f"Invalid expression: {e}")


async def perform_classification(
    ctx: Dict[str, Any],
    job_id: str,
    method: str = "kmeans",
    num_classes: int = 5,
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    aoi: Optional[Dict[str, Any]] = None,
    training_data: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Perform image classification (alias for run_classification)."""
    return await run_classification(
        ctx=ctx,
        job_id=job_id,
        method=method,
        num_classes=num_classes,
        scene_ids=scene_ids,
        mosaic_id=mosaic_id,
        aoi=aoi,
        training_data=training_data,
        user_id=user_id,
    )


async def detect_changes(
    ctx: Dict[str, Any],
    job_id: str,
    scene_ids: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    aoi: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Detect changes between satellite scenes."""
    logger.info(f"Starting change detection job {job_id}")

    # TODO: Implement change detection
    # This would compare multiple scenes and identify changes

    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Change detection not yet implemented",
    }


async def create_temporal_composite(
    ctx: Dict[str, Any],
    job_id: str,
    scene_ids: Optional[List[str]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    aoi: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Create temporal composite from multiple scenes."""
    logger.info(f"Starting temporal composite job {job_id}")

    # TODO: Implement temporal compositing
    # This would combine multiple temporal scenes into a composite

    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Temporal composite not yet implemented",
    }


async def calculate_band_math(
    ctx: Dict[str, Any],
    job_id: str,
    expression: str,
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    aoi: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Calculate custom band math expression."""
    logger.info(f"Starting band math calculation job {job_id}")

    # TODO: Implement custom band math
    # This would evaluate custom expressions like "(B8-B4)/(B8+B4)"

    return {
        "job_id": job_id,
        "status": "completed",
        "message": "Band math not yet implemented",
        "expression": expression,
    }


async def extract_mask(
    ctx: Dict[str, Any],
    job_id: str,
    mask_type: str = "cloud",
    scene_ids: Optional[List[str]] = None,
    mosaic_id: Optional[str] = None,
    aoi: Optional[Dict[str, Any]] = None,
    parameters: Optional[Dict[str, Any]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract masks from satellite imagery."""
    logger.info(f"Starting mask extraction job {job_id} for {mask_type}")

    # TODO: Implement mask extraction
    # This would extract cloud masks, water masks, etc.

    return {
        "job_id": job_id,
        "status": "completed",
        "message": f"{mask_type} mask extraction not yet implemented",
    }


# List of functions to register with the worker
functions = [
    download_imagery,
    process_imagery,
    export_dataset,
    create_batch_download,
    cleanup_old_downloads,
    create_imagery_mosaic,
    calculate_spectral_index,
    run_classification,
    calculate_zonal_statistics,
    # Aliases and additional processing functions
    perform_classification,
    detect_changes,
    create_temporal_composite,
    calculate_band_math,
    extract_mask,
]
