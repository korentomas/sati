"""Service for handling direct downloads to user's computer."""

import os
from pathlib import Path
from typing import Optional

from fastapi import HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
import aiofiles


class DirectDownloadService:
    """Handle direct file downloads to user's computer."""

    @staticmethod
    async def download_processed_image(
        file_path: str,
        filename: Optional[str] = None,
    ) -> FileResponse:
        """
        Stream a processed image directly to user's browser for download.

        Args:
            file_path: Path to the processed image on server
            filename: Optional custom filename for download

        Returns:
            FileResponse that triggers browser download
        """
        # Validate file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )

        # Get filename for download
        if not filename:
            filename = Path(file_path).name

        # Return file for download
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type='application/octet-stream',
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    @staticmethod
    async def stream_large_file(file_path: str, chunk_size: int = 1024 * 1024):
        """
        Stream large files in chunks to avoid memory issues.

        Args:
            file_path: Path to file
            chunk_size: Size of each chunk (default 1MB)
        """
        async with aiofiles.open(file_path, 'rb') as f:
            while chunk := await f.read(chunk_size):
                yield chunk

    @staticmethod
    async def download_from_url(
        image_url: str,
        processed: bool = False,
    ) -> StreamingResponse:
        """
        Download image from URL and stream to user.

        This is for real-time downloads without queuing.
        Useful for small images or processed results.

        Args:
            image_url: URL of the image to download
            processed: Whether this is a processed result

        Returns:
            StreamingResponse for immediate download
        """
        import httpx

        async def stream_from_url():
            async with httpx.AsyncClient() as client:
                async with client.stream('GET', image_url) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        # Determine filename and media type
        filename = image_url.split('/')[-1].split('?')[0] or 'download.tif'
        media_type = 'image/tiff' if filename.endswith('.tif') else 'application/octet-stream'

        return StreamingResponse(
            stream_from_url(),
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )