# Docker Setup Guide

This guide explains how to run the SATI Backend using Docker.

## Prerequisites

- Docker Desktop installed and running
- Docker Compose (included with Docker Desktop)
- Git

## Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/korentomas/sati.git
cd sati/sati-be
```

### 2. Set up environment variables
```bash
# Copy the Docker example environment file
cp .env.docker.example .env

# Edit .env file with your settings (especially SECRET_KEY)
nano .env  # or use your preferred editor
```

### 3. Build and run with Docker Compose
```bash
# Build and start all services
make up

# Or directly with docker-compose
docker-compose up --build
```

### 4. Verify the setup
The API should be available at:
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/v1/docs
- **Health Check**: http://localhost:8000/api/v1/health/live

## Services

Docker Compose starts three services:

1. **api** - The FastAPI backend application
2. **db** - PostgreSQL database
3. **redis** - Redis cache (for future features)

## Common Commands

### Start services
```bash
make up                    # Start in background
docker-compose up          # Start with logs
```

### Stop services
```bash
make down                  # Stop all services
docker-compose down        # Stop and remove containers
docker-compose down -v     # Also remove volumes (data)
```

### View logs
```bash
docker-compose logs        # All services
docker-compose logs api    # Only API logs
docker-compose logs -f api # Follow API logs
```

### Rebuild after code changes
```bash
make build                 # Rebuild images
docker-compose build       # Same as above
```

### Access database
```bash
docker-compose exec db psql -U satellite_user -d satellite_imagery
```

### Run tests
```bash
docker-compose exec api pytest
```

## Development Mode

For development with hot-reload:
```bash
docker-compose up
```

The `docker-compose.yml` is configured with:
- Volume mounting of `./app` for hot-reload
- Port forwarding for debugging
- Development environment settings

## Production Deployment

For production:

1. Update `.env` with production values:
   - Set `ENVIRONMENT=production`
   - Set `DEBUG=false`
   - Use a strong `SECRET_KEY`
   - Configure production database URL

2. Remove volume mounts from `docker-compose.yml`

3. Use production command:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

## Troubleshooting

### Port already in use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process or change the port in docker-compose.yml
```

### Database connection issues
```bash
# Ensure database is running
docker-compose ps

# Check database logs
docker-compose logs db

# Recreate database
docker-compose down -v
docker-compose up --build
```

### Permission issues
```bash
# The Dockerfile creates a non-root user (appuser)
# If you have permission issues, check file ownership:
ls -la app/

# Fix permissions if needed:
sudo chown -R $(whoami):$(whoami) app/
```

## Environment Variables

Key environment variables (see `.env.docker.example`):

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key (CHANGE IN PRODUCTION!)
- `DEBUG` - Debug mode (false for production)
- `LOG_LEVEL` - Logging level (INFO, DEBUG, ERROR)

## Architecture

The Docker setup uses:
- **Python 3.11** - Base image
- **PostgreSQL 15** - Database
- **Redis 7** - Cache
- **GDAL** - Geospatial libraries for imagery processing

## Security Notes

1. Always change the default `SECRET_KEY` in production
2. Use strong passwords for database
3. Don't expose database ports in production
4. Use HTTPS in production (add reverse proxy like nginx)
5. Keep Docker images updated

## Support

For issues or questions:
- Check the [main README](README.md)
- Open an issue on GitHub
- Review the [API documentation](http://localhost:8000/api/v1/docs)
