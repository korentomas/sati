from datetime import datetime
from typing import Any, Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/live")
async def liveness_check() -> Dict[str, Any]:
    """Liveness probe for container orchestration."""
    return {"status": "alive", "timestamp": datetime.utcnow()}


@router.get("/ready")
async def readiness_check() -> Dict[str, Any]:
    """Readiness probe for container orchestration."""
    # TODO: Add actual readiness checks (DB connection, Redis, etc.)
    return {
        "status": "ready",
        "timestamp": datetime.utcnow(),
        "services": {"database": "healthy", "redis": "healthy"},
    }
