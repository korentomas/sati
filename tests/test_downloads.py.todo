"""Tests for parallel download functionality with Arq."""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from arq import ArqRedis
from fastapi import status
from httpx import AsyncClient

from app.workers.tasks import (
    calculate_file_hash,
    download_imagery,
    export_dataset,
    get_job_status,
    process_imagery,
    update_job_status,
)


@pytest.mark.asyncio
class TestDownloadEndpoints:
    """Test download API endpoints."""

    async def test_queue_download_success(
        self, async_client: AsyncClient, authenticated_headers: dict
    ):
        """Test successful download job queuing."""
        with patch(
            "app.api.v1.features.imagery.downloads.router.get_redis_pool"
        ) as mock_pool:
            mock_redis = AsyncMock(spec=ArqRedis)
            mock_redis.enqueue_job.return_value = MagicMock()
            mock_pool.return_value = mock_redis

            response = await async_client.post(
                "/api/v1/downloads/download",
                headers=authenticated_headers,
                json={
                    "urls": [
                        "https://example.com/image1.tif",
                        "https://example.com/image2.tif",
                    ],
                    "priority": 8,
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "Download job queued with 2 file(s)" in data["message"]

    async def test_get_job_status(
        self, async_client: AsyncClient, authenticated_headers: dict
    ):
        """Test getting job status."""
        job_id = str(uuid4())

        with patch(
            "app.api.v1.features.imagery.downloads.router.get_redis_pool"
        ) as mock_pool:
            mock_redis = AsyncMock(spec=ArqRedis)
            mock_redis.get.return_value = json.dumps(
                {
                    "status": "in_progress",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "total": 5,
                    "completed": 3,
                    "percentage": 60,
                }
            )
            mock_pool.return_value = mock_redis

            response = await async_client.get(
                f"/api/v1/downloads/jobs/{job_id}",
                headers=authenticated_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["job_id"] == job_id
            assert data["status"] == "in_progress"
            assert data["progress"]["completed"] == 3

    async def test_cancel_job(
        self, async_client: AsyncClient, authenticated_headers: dict
    ):
        """Test cancelling a job."""
        job_id = str(uuid4())

        with patch(
            "app.api.v1.features.imagery.downloads.router.get_redis_pool"
        ) as mock_pool:
            mock_redis = AsyncMock(spec=ArqRedis)
            mock_redis.get.return_value = json.dumps({"status": "pending"})
            mock_redis.abort_job.return_value = True
            mock_pool.return_value = mock_redis

            response = await async_client.post(
                f"/api/v1/downloads/jobs/{job_id}/cancel",
                headers=authenticated_headers,
                json={"reason": "User requested cancellation"},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == "cancelled"
            assert "Job cancelled successfully" in data["message"]

    async def test_export_dataset(
        self, async_client: AsyncClient, authenticated_headers: dict
    ):
        """Test dataset export."""
        with patch(
            "app.api.v1.features.imagery.downloads.router.get_redis_pool"
        ) as mock_pool:
            mock_redis = AsyncMock(spec=ArqRedis)
            mock_redis.enqueue_job.return_value = MagicMock()
            mock_pool.return_value = mock_redis

            response = await async_client.post(
                "/api/v1/downloads/export",
                headers=authenticated_headers,
                json={
                    "file_paths": ["/downloads/image1.tif", "/downloads/image2.tif"],
                    "export_format": "zip",
                },
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert "job_id" in data
            assert data["status"] == "pending"
            assert "Export job queued for 2 file(s)" in data["message"]


@pytest.mark.asyncio
class TestDownloadTasks:
    """Test Arq worker tasks."""

    async def test_download_imagery_success(self, tmp_path):
        """Test successful image download."""
        ctx = {"redis": AsyncMock(spec=ArqRedis)}
        job_id = str(uuid4())
        urls = ["https://example.com/image.tif"]
        user_id = "test_user"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_response = AsyncMock()
            mock_response.raise_for_status = MagicMock()
            mock_response.aiter_bytes = AsyncMock(return_value=iter([b"test_data"]))
            mock_client.get.return_value = mock_response
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("app.workers.tasks.DOWNLOAD_DIR", tmp_path):
                result = await download_imagery(ctx, job_id, urls, user_id)

            assert result["status"] == "completed"
            assert result["summary"]["successful"] == 1
            assert result["summary"]["failed"] == 0
            assert len(result["results"]) == 1

    async def test_download_imagery_partial_failure(self, tmp_path):
        """Test partial download failure."""
        ctx = {"redis": AsyncMock(spec=ArqRedis)}
        job_id = str(uuid4())
        urls = ["https://example.com/image1.tif", "https://example.com/image2.tif"]
        user_id = "test_user"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()

            # First download succeeds
            mock_response_success = AsyncMock()
            mock_response_success.raise_for_status = MagicMock()
            mock_response_success.aiter_bytes = AsyncMock(
                return_value=iter([b"test_data"])
            )

            # Second download fails
            mock_response_fail = AsyncMock()
            mock_response_fail.raise_for_status.side_effect = Exception(
                "Download failed"
            )

            mock_client.get.side_effect = [mock_response_success, mock_response_fail]
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with patch("app.workers.tasks.DOWNLOAD_DIR", tmp_path):
                result = await download_imagery(ctx, job_id, urls, user_id)

            assert result["status"] == "partial"
            assert result["summary"]["successful"] == 1
            assert result["summary"]["failed"] == 1

    async def test_export_dataset_zip(self, tmp_path):
        """Test exporting dataset as zip."""
        ctx = {"redis": AsyncMock(spec=ArqRedis)}
        job_id = str(uuid4())
        user_id = "test_user"

        # Create test files
        test_files = []
        for i in range(3):
            file_path = tmp_path / f"test_{i}.tif"
            file_path.write_text(f"test content {i}")
            test_files.append(str(file_path))

        with patch("app.workers.tasks.DOWNLOAD_DIR", tmp_path):
            result = await export_dataset(ctx, job_id, test_files, "zip", user_id)

        assert result["status"] == "completed"
        assert result["export_format"] == "zip"
        assert result["file_count"] == 3
        assert result["export_size"] > 0

    async def test_process_imagery(self):
        """Test image processing task."""
        ctx = {"redis": AsyncMock(spec=ArqRedis)}
        job_id = str(uuid4())
        filepath = "/test/image.tif"
        operations = [{"type": "resize", "width": 512, "height": 512}]
        user_id = "test_user"

        result = await process_imagery(ctx, job_id, filepath, operations, user_id)

        assert result["status"] == "completed"
        assert result["original_file"] == filepath
        assert "_processed.tif" in result["processed_file"]

    async def test_update_and_get_job_status(self):
        """Test job status update and retrieval."""
        mock_redis = AsyncMock(spec=ArqRedis)
        job_id = str(uuid4())

        # Test update
        await update_job_status(
            mock_redis,
            job_id,
            "in_progress",
            {"total": 10, "completed": 5},
        )

        # Verify set was called
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert f"job:status:{job_id}" in call_args[0]

        # Test get
        mock_redis.get.return_value = json.dumps(
            {
                "status": "in_progress",
                "total": 10,
                "completed": 5,
            }
        )

        status = await get_job_status(mock_redis, job_id)
        assert status["status"] == "in_progress"
        assert status["completed"] == 5

    async def test_calculate_file_hash(self, tmp_path):
        """Test file hash calculation."""
        test_file = tmp_path / "test.bin"
        test_content = b"test content for hashing"
        test_file.write_bytes(test_content)

        hash_result = await calculate_file_hash(test_file)

        # Verify it's a valid SHA256 hash (64 hex characters)
        assert len(hash_result) == 64
        assert all(c in "0123456789abcdef" for c in hash_result)
