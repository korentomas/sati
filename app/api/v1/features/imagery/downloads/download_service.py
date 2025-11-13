"""Service for handling direct downloads to user's computer."""

from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import HTTPException, status
from fastapi.responses import FileResponse, StreamingResponse
from werkzeug.utils import secure_filename


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
        # Sanitize file path to prevent path traversal
        safe_path = Path(file_path).resolve()

        # Define allowed download directory
        allowed_base = Path("/app/downloads").resolve()

        # Verify the resolved path is within allowed directory
        try:
            # Raises ValueError if safe_path is not inside allowed_base
            safe_path.relative_to(allowed_base)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        # Validate file exists
        if not safe_path.exists():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="File not found"
            )

        # Get filename for download
        if not filename:
            filename = safe_path.name

        # Sanitize filename to prevent header injection
        import re

        filename = secure_filename(filename)

        # Return file for download
        return FileResponse(
            path=str(safe_path),
            filename=filename,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    @staticmethod
    async def stream_large_file(file_path: str, chunk_size: int = 1024 * 1024):
        """
        Stream large files in chunks to avoid memory issues.

        Args:
            file_path: Path to file
            chunk_size: Size of each chunk (default 1MB)
        """
        # Sanitize file path to prevent path traversal
        safe_path = Path(file_path).resolve()

        # Define allowed download directory
        allowed_base = Path("/app/downloads").resolve()

        # Verify the resolved path is within allowed directory
        if not str(safe_path).startswith(str(allowed_base)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Access denied"
            )

        async with aiofiles.open(str(safe_path), "rb") as f:
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
        import ipaddress
        import re
        import socket
        from urllib.parse import urlparse

        import httpx

        # Validate URL format
        try:
            parsed = urlparse(image_url)
            if parsed.scheme not in ["http", "https"]:
                raise ValueError("Only HTTP/HTTPS URLs are allowed")
            if not parsed.netloc:
                raise ValueError("Invalid URL")
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid URL format"
            )

        # Define allowed domains for satellite imagery
        ALLOWED_DOMAINS = [
            "sentinel-hub.com",
            "scihub.copernicus.eu",
            "earthexplorer.usgs.gov",
            "planet.com",
            "unsplash.com",  # For testing
            "amazonaws.com",  # For S3 buckets
        ]

        # Check if domain is in allowed list
        domain = parsed.netloc.lower()
        if not any(allowed in domain for allowed in ALLOWED_DOMAINS):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="URL domain not allowed"
            )

        # Prevent SSRF to internal IPs
        try:
            # Resolve hostname to IP
            hostname = parsed.netloc.split(":")[0]
            ip = socket.gethostbyname(hostname)
            ip_obj = ipaddress.ip_address(ip)

            # Block private and loopback IPs
            if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Access to internal resources not allowed",
                )
        except socket.gaierror:
            pass  # Unable to resolve, let httpx handle it

        async def stream_from_url():
            async with httpx.AsyncClient(
                timeout=30.0, follow_redirects=False
            ) as client:
                async with client.stream("GET", image_url) as response:
                    response.raise_for_status()
                    async for chunk in response.aiter_bytes():
                        yield chunk

        # Sanitize filename to prevent header injection
        filename = image_url.split("/")[-1].split("?")[0] or "download.tif"
        filename = re.sub(r"[^\w\s.-]", "", filename)
        media_type = (
            "image/tiff" if filename.endswith(".tif") else "application/octet-stream"
        )

        return StreamingResponse(
            stream_from_url(),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )
