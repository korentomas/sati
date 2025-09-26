"""Router for imagery search endpoints."""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.v1.features.imagery.search.schemas import (
    CollectionInfo,
    SceneResponse,
    SearchRequest,
    SearchResponse,
)
from app.api.v1.features.imagery.search.service import SearchService
from app.api.v1.shared.auth.deps import get_current_user
from app.core.logging import logger

router = APIRouter()


@router.get("/collections", response_model=List[CollectionInfo])
async def list_collections(
    current_user: dict = Depends(get_current_user),
) -> List[CollectionInfo]:
    """List all available satellite imagery collections.

    Returns information about available data sources like Sentinel-2, Landsat, etc.
    """
    try:
        service = SearchService()
        return await service.list_collections()
    except Exception as e:
        logger.error(f"Failed to list collections: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve collections")


@router.post("/search", response_model=SearchResponse)
async def search_imagery(
    request: SearchRequest,
    current_user: dict = Depends(get_current_user),
) -> SearchResponse:
    """Search for satellite imagery.

    Search can be performed using either:
    - A GeoJSON polygon geometry (from map drawing)
    - A bounding box [west, south, east, north]

    Filters include:
    - Date range
    - Maximum cloud cover
    - Specific satellite collections
    """
    try:
        service = SearchService()
        return await service.search_imagery(request)
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail="Search failed")


@router.get("/scenes/{collection_id}/{scene_id}", response_model=SceneResponse)
async def get_scene(
    collection_id: str,
    scene_id: str,
    current_user: dict = Depends(get_current_user),
) -> SceneResponse:
    """Get detailed information about a specific scene.

    Returns metadata, available assets, and preview URLs for a specific satellite image.
    """
    try:
        service = SearchService()
        scene = await service.get_scene(collection_id, scene_id)

        if not scene:
            raise HTTPException(status_code=404, detail="Scene not found")

        return scene
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get scene: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve scene")
