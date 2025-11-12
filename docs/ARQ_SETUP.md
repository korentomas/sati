# Arq Worker Setup for Parallel Downloads

This document explains how to use the Arq-based parallel download system for satellite imagery.

## Overview

The SATI Backend uses [Arq](https://github.com/samuelcolvin/arq) for background job processing, enabling:
- **Parallel downloads** of multiple satellite images
- **Streaming downloads** to handle large files efficiently
- **Job status tracking** in real-time
- **Automatic retries** for failed downloads
- **Dataset exports** in various formats

## Architecture

```
Users → FastAPI → Redis Queue → Arq Workers → Download/Process → Storage
           ↓                          ↑
      Status API ←──────────────────────
```

## Quick Start

### 1. Start Services with Workers

```bash
# Start Redis and PostgreSQL
make services-up

# In terminal 1: Start the API server
make dev

# In terminal 2: Start Arq workers
make worker
```

### 2. Using Docker (Recommended)

```bash
# Start everything with Docker Compose
docker-compose up

# This starts:
# - API server (port 8000)
# - 2 Arq worker instances
# - PostgreSQL database
# - Redis for job queue
```

## API Endpoints

### Queue Downloads

**POST** `/api/v1/downloads/download`

Queue multiple satellite images for parallel download:

```json
{
  "urls": [
    "https://example.com/sentinel2/image1.tif",
    "https://example.com/sentinel2/image2.tif",
    "https://example.com/sentinel2/image3.tif"
  ],
  "priority": 8,
  "metadata": {
    "collection": "sentinel-2",
    "date_range": "2024-01-01/2024-01-31"
  }
}
```

Response:
```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "created_at": "2024-01-15T10:30:00Z",
  "queue_position": 3,
  "estimated_time": 90,
  "message": "Download job queued with 3 file(s)"
}
```

### Check Job Status

**GET** `/api/v1/downloads/jobs/{job_id}`

Monitor download progress:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "in_progress",
  "progress": {
    "total": 3,
    "completed": 2,
    "percentage": 66.67,
    "current_file": "image3.tif"
  },
  "updated_at": "2024-01-15T10:31:30Z"
}
```

### Get Download Results

**GET** `/api/v1/downloads/jobs/{job_id}/result`

Retrieve completed download information:

```json
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": [
    {
      "url": "https://example.com/sentinel2/image1.tif",
      "filepath": "/downloads/user_123/job_550e/image1.tif",
      "filename": "image1.tif",
      "size": 524288000,
      "hash": "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3",
      "downloaded_at": "2024-01-15T10:31:00Z"
    }
  ],
  "summary": {
    "total_requested": 3,
    "successful": 3,
    "failed": 0,
    "total_size": 1572864000
  }
}
```

### Export Dataset

**POST** `/api/v1/downloads/export`

Export multiple files as a compressed dataset:

```json
{
  "file_paths": [
    "/downloads/image1.tif",
    "/downloads/image2.tif"
  ],
  "export_format": "zip",
  "include_metadata": true
}
```

### Cancel Job

**POST** `/api/v1/downloads/jobs/{job_id}/cancel`

Cancel a pending or running job:

```json
{
  "reason": "User requested cancellation"
}
```

### List Jobs

**GET** `/api/v1/downloads/jobs`

List all jobs with optional filtering:

```
GET /api/v1/downloads/jobs?status_filter=completed&page=1&per_page=20
```

## Worker Configuration

Workers are configured in `app/workers/config.py`:

```python
class WorkerSettings:
    max_jobs = 10           # Concurrent jobs per worker
    job_timeout = 3600      # 1 hour timeout
    max_tries = 3           # Retry failed jobs 3 times
    max_burst_jobs = 20     # Process up to 20 jobs in burst
```

## Parallel Processing

### How It Works

1. **Job Queuing**: Downloads are queued in Redis with priorities
2. **Worker Pool**: Multiple workers process jobs concurrently
3. **Parallel Downloads**: Each worker can download multiple files in parallel (default: 5 concurrent downloads)
4. **Progress Tracking**: Real-time progress updates via Redis
5. **Result Storage**: Downloaded files stored in `/downloads/{user_id}/{job_id}/`

### Performance Tuning

Adjust parallelism based on your needs:

```python
# In app/workers/tasks.py
semaphore = asyncio.Semaphore(5)  # Concurrent downloads per job

# In docker-compose.yml
deploy:
  replicas: 2  # Number of worker instances
```

## Development

### Running Workers Locally

```bash
# Start worker with auto-reload (requires watchdog)
pip install watchdog
make worker-dev

# Or run directly
arq app.workers.worker.WorkerConfig
```

### Testing

Run tests for download functionality:

```bash
pytest tests/test_downloads.py -v
```

### Monitoring

Monitor Redis queue:

```bash
# Connect to Redis
redis-cli

# Check queue size
LLEN arq:queue
LLEN arq:downloads

# Monitor in real-time
redis-cli MONITOR | grep arq
```

## Production Considerations

### Scaling

1. **Horizontal Scaling**: Increase worker replicas in `docker-compose.yml`
2. **Vertical Scaling**: Increase `max_jobs` per worker
3. **Queue Prioritization**: Use priority levels (1-10) for important downloads

### Storage

1. **Cleanup**: Old downloads are automatically cleaned after 7 days
2. **Volume Mounting**: Ensure `/downloads` is on sufficient storage
3. **Cloud Storage**: Consider S3/GCS for production deployments

### Monitoring & Logging

1. **Health Checks**: Workers perform health checks every 60 seconds
2. **Logging**: All operations logged via Loguru
3. **Metrics**: Track job completion rates, download speeds, failure rates

### Error Handling

1. **Automatic Retries**: Failed downloads retry up to 3 times
2. **Partial Success**: Batch downloads can partially succeed
3. **Error Reporting**: Detailed error messages in job status

## Environment Variables

Required for workers:

```bash
REDIS_URL=redis://localhost:6379
DATABASE_URL=postgresql://user:pass@localhost/db
SECRET_KEY=your-secret-key
LOG_LEVEL=INFO
```

## Troubleshooting

### Workers Not Processing Jobs

```bash
# Check worker logs
docker-compose logs worker

# Verify Redis connection
redis-cli ping

# Check for stuck jobs
arq --redis redis://localhost:6379 info
```

### Download Failures

1. Check network connectivity
2. Verify URLs are accessible
3. Check disk space in `/downloads`
4. Review worker logs for errors

### Performance Issues

1. Increase worker replicas
2. Adjust concurrent download limit
3. Check Redis memory usage
4. Monitor network bandwidth

## Example Use Cases

### Bulk Download Sentinel-2 Images

```python
import httpx
import asyncio

async def bulk_download():
    async with httpx.AsyncClient() as client:
        # Queue download job
        response = await client.post(
            "http://localhost:8000/api/v1/downloads/download",
            json={
                "urls": [f"https://example.com/image_{i}.tif" for i in range(100)],
                "priority": 10
            },
            headers={"Authorization": "Bearer YOUR_TOKEN"}
        )
        job_id = response.json()["job_id"]

        # Poll for completion
        while True:
            status_response = await client.get(
                f"http://localhost:8000/api/v1/downloads/jobs/{job_id}",
                headers={"Authorization": "Bearer YOUR_TOKEN"}
            )
            status = status_response.json()["status"]

            if status == "completed":
                break
            elif status == "failed":
                raise Exception("Download failed")

            await asyncio.sleep(5)

        # Get results
        results = await client.get(
            f"http://localhost:8000/api/v1/downloads/jobs/{job_id}/result",
            headers={"Authorization": "Bearer YOUR_TOKEN"}
        )
        return results.json()

# Run the download
results = asyncio.run(bulk_download())
print(f"Downloaded {results['summary']['successful']} files")
```

## Support

For issues or questions:
- Check the [main README](../README.md)
- Review worker logs: `docker-compose logs worker`
- Open an issue on GitHub