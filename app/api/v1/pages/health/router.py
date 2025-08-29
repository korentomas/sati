from fastapi import APIRouter
from datetime import datetime

router = APIRouter()


@router.get("/live")
async def liveness_check():
    """Liveness probe for container orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/ready")
async def readiness_check():
    """Readiness probe for container orchestration."""
    # TODO: Add actual readiness checks (DB connection, Redis, etc.)
    return {
        "status": "ready",
        "timestamp": datetime.utcnow(),
        "services": {
            "database": "healthy",
            "redis": "healthy"
        }
    }