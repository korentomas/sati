from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.features.authentication.router import router as auth_router
from app.api.v1.pages.health.router import router as health_router
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
logger = setup_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=settings.description,
    openapi_url=f"{settings.api_v1_prefix}/openapi.json",
    docs_url=f"{settings.api_v1_prefix}/docs",
    redoc_url=f"{settings.api_v1_prefix}/redoc",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    health_router, prefix=f"{settings.api_v1_prefix}/health", tags=["health"]
)
app.include_router(
    auth_router, prefix=f"{settings.api_v1_prefix}/auth", tags=["authentication"]
)


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.version,
        "docs": f"{settings.api_v1_prefix}/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
