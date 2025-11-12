"""Background tasks for satellite imagery downloads and processing."""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import aiofiles
import httpx
from arq import ArqRedis
from loguru import logger

from app.core.config import settings

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
    await update_job_status(redis, job_id, "in_progress", {"total": len(urls), "completed": 0})

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
                    filename = url.split("/")[-1] or f"image_{index}_{uuid4().hex[:8]}.tif"
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
                    mtime = datetime.fromtimestamp(job_dir.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        # Calculate size before deletion
                        size = sum(f.stat().st_size for f in job_dir.rglob("*") if f.is_file())
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
    key = f"job:status:{job_id}"
    value = json.dumps(
        {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **data,
        }
    )
    await redis.set(key, value, ex=3600)  # Expire after 1 hour


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


# List of functions to register with the worker
functions = [
    download_imagery,
    process_imagery,
    export_dataset,
    cleanup_old_downloads,
]