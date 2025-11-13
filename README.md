# SATI Backend - Satellite Imagery Gateway API

A high-performance FastAPI backend for satellite imagery search, download, and processing with parallel job processing using Arq.

## Features

- **Authentication System**: JWT-based authentication with SQLAlchemy
- **User Management**: User registration and login with secure password hashing
- **Satellite Imagery Search**: Search and filter satellite imagery from multiple sources
- **Parallel Downloads**: High-performance parallel download system using Arq workers
- **Background Processing**: Asynchronous job queue for long-running tasks
- **STAC Integration**: Built on STAC (SpatioTemporal Asset Catalog) standards
- **Tile Server**: Dynamic tile generation for map visualization
- **GeoJSON Support**: Full support for geographic data formats
- **Cloud-Optimized**: Ready for cloud deployment with Docker

## Tech Stack

- **FastAPI**: Modern async Python web framework
- **PostgreSQL**: Primary database with PostGIS support
- **Redis**: Cache and job queue backend
- **Arq**: Async job queue for parallel processing
- **SQLAlchemy**: ORM for database operations
- **GDAL/Rasterio**: Geospatial data processing
- **Docker**: Containerization for easy deployment

## Quick Start

### Option 1: Development with Services in Docker

```bash
# Clone the repository
git clone https://github.com/korentomas/sati.git
cd sati/sati-be

# Copy environment configuration
cp .env.example .env

# Start PostgreSQL and Redis in Docker
make services-up

# In terminal 1: Start the API server
make dev

# In terminal 2: Start Arq workers for parallel downloads
make worker
```

### Option 2: Full Docker Setup

```bash
# Build and run all services (API, Workers, Redis, PostgreSQL)
docker-compose up --build

# This starts:
# - API server on port 8000
# - 2 Arq worker instances for parallel processing
# - PostgreSQL database
# - Redis for caching and job queue
```

### Option 3: Manual Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run the development server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# In another terminal, run workers
arq app.workers.worker.WorkerConfig
```

## API Documentation

Once running, you can access:

- **Swagger UI**: http://localhost:8000/api/v1/docs
- **ReDoc**: http://localhost:8000/api/v1/redoc
- **Health Check**: http://localhost:8000/api/v1/health/live

## Key Endpoints

### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - Login and get JWT token
- `POST /api/v1/auth/api-key` - Generate API key

### Satellite Imagery
- `GET /api/v1/imagery/collections` - List available satellite collections
- `POST /api/v1/imagery/search` - Search for satellite imagery
- `GET /api/v1/imagery/tiles/{z}/{x}/{y}` - Get map tiles

### Parallel Downloads (NEW)
- `POST /api/v1/downloads/download` - Queue parallel downloads
- `GET /api/v1/downloads/jobs/{job_id}` - Check job status
- `GET /api/v1/downloads/jobs/{job_id}/result` - Get download results
- `POST /api/v1/downloads/export` - Export dataset
- `POST /api/v1/downloads/jobs/{job_id}/cancel` - Cancel job

## Parallel Download System

The backend includes a powerful parallel download system using Arq:

```python
# Example: Queue multiple satellite images for download
POST /api/v1/downloads/download
{
  "urls": [
    "https://example.com/image1.tif",
    "https://example.com/image2.tif",
    "https://example.com/image3.tif"
  ],
  "priority": 8
}

# Response includes job_id for tracking
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Download job queued with 3 file(s)"
}
```

See [ARQ_SETUP.md](docs/ARQ_SETUP.md) for detailed documentation on the parallel download system.

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_downloads.py -v
```

### Code Quality

```bash
# Run linting
make lint

# Auto-format code
make format

# Run all checks
make check-all
```

### Database Migrations

```bash
# Initialize Alembic (if not done)
alembic init alembic

# Create a new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head
```

## Project Structure

```
sati-be/
├── app/
│   ├── api/v1/
│   │   ├── features/
│   │   │   ├── authentication/  # Auth endpoints
│   │   │   ├── imagery/        # Imagery search & downloads
│   │   │   └── downloads/      # Parallel download system
│   │   └── shared/             # Shared utilities
│   ├── core/                   # Core configuration
│   ├── workers/                # Arq background workers
│   │   ├── config.py          # Worker configuration
│   │   ├── tasks.py           # Download & processing tasks
│   │   └── worker.py          # Worker entry point
│   └── main.py                # FastAPI app
├── tests/                     # Test suite
├── docs/                      # Documentation
│   ├── ARQ_SETUP.md          # Arq worker documentation
│   └── DOCKER_SETUP.md       # Docker setup guide
├── docker-compose.yml         # Docker orchestration
├── Dockerfile                # Container definition
├── Makefile                  # Development commands
└── requirements.txt          # Python dependencies
```

## Environment Variables

Key environment variables (see `.env.example`):

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/satellite_imagery

# Redis
REDIS_URL=redis://localhost:6379

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30

# External APIs (future implementation)
NASA_EARTHDATA_USERNAME=your_username
NASA_EARTHDATA_PASSWORD=your_password
```

## Performance

The system is designed for high performance:

- **Async/await** throughout for non-blocking I/O
- **Parallel downloads** with configurable concurrency
- **Redis caching** for frequently accessed data
- **Connection pooling** for database efficiency
- **Background workers** for long-running tasks

## Docker Support

Full Docker support with:
- Multi-stage builds for optimized images
- Docker Compose for local development
- Volume mounting for hot-reload
- Health checks for all services

See [DOCKER_SETUP.md](docs/DOCKER_SETUP.md) for detailed Docker instructions.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues or questions:
- Open an issue on [GitHub](https://github.com/korentomas/sati/issues)
- Check the documentation in `/docs`
- Review API documentation at `/api/v1/docs` when running

## Roadmap

- [x] Basic authentication system
- [x] SQLAlchemy migration from Supabase
- [x] Parallel download system with Arq
- [ ] Sentinel Hub integration
- [ ] NASA Earthdata integration
- [ ] Cloud storage support (S3/GCS)
- [ ] Advanced image processing pipeline
- [ ] WebSocket support for real-time updates
