"""STAC client for AWS Earth Search."""

from typing import Any, Dict, List, Optional

import httpx
from httpx import AsyncClient

from app.api.v1.features.imagery.stac.models import (
    STACCollection,
    STACItem,
    STACItemCollection,
)
from app.core.logging import logger


class STACClient:
    """Client for interacting with STAC APIs."""

    def __init__(self, api_url: str = "https://earth-search.aws.element84.com/v1"):
        """Initialize STAC client.

        Args:
            api_url: Base URL for STAC API (defaults to AWS Earth Search)
        """
        self.api_url = api_url
        self.client = AsyncClient(timeout=30.0)

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.client.aclose()

    async def list_collections(self) -> List[STACCollection]:
        """List all available collections."""
        try:
            response = await self.client.get(f"{self.api_url}/collections")
            response.raise_for_status()
            data = response.json()

            collections = []
            for coll_data in data.get("collections", []):
                collections.append(STACCollection(**coll_data))

            return collections
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def get_collection(self, collection_id: str) -> Optional[STACCollection]:
        """Get a specific collection by ID."""
        try:
            response = await self.client.get(
                f"{self.api_url}/collections/{collection_id}"
            )
            response.raise_for_status()
            return STACCollection(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get collection {collection_id}: {e}")
            raise

    async def search(
        self,
        collections: Optional[List[str]] = None,
        bbox: Optional[List[float]] = None,
        datetime: Optional[str] = None,
        limit: int = 10,
        query: Optional[Dict[str, Any]] = None,
    ) -> STACItemCollection:
        """Search for items across collections.

        Args:
            collections: List of collection IDs to search
            bbox: Bounding box [west, south, east, north]
            datetime: Date range (e.g., "2024-01-01/2024-12-31")
            limit: Maximum number of results
            query: Additional query parameters (e.g., {"eo:cloud_cover": {"lt": 20}})
        """
        payload = {
            "limit": limit,
        }

        if collections:
            payload["collections"] = collections
        if bbox:
            payload["bbox"] = bbox
        if datetime:
            payload["datetime"] = datetime
        if query:
            payload["query"] = query

        try:
            response = await self.client.post(
                f"{self.api_url}/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            # Parse items
            items = []
            for feature in data.get("features", []):
                items.append(STACItem(**feature))

            return STACItemCollection(
                type=data.get("type", "FeatureCollection"),
                features=items,
                links=data.get("links", []),
                context=data.get("context"),
            )
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def search_with_geometry(
        self,
        geometry: Dict[str, Any],
        collections: Optional[List[str]] = None,
        datetime: Optional[str] = None,
        limit: int = 10,
        cloud_cover_max: Optional[float] = None,
    ) -> STACItemCollection:
        """Search with a GeoJSON geometry (polygon).

        Args:
            geometry: GeoJSON geometry (e.g., Polygon from user drawing)
            collections: List of collection IDs
            datetime: Date range
            limit: Maximum results
            cloud_cover_max: Maximum cloud cover percentage
        """
        payload = {
            "intersects": geometry,
            "limit": limit,
        }

        if collections:
            payload["collections"] = collections
        if datetime:
            payload["datetime"] = datetime

        # Add cloud cover filter if specified
        if cloud_cover_max is not None and cloud_cover_max < 100:
            payload["query"] = {"eo:cloud_cover": {"lt": cloud_cover_max}}

        try:
            response = await self.client.post(
                f"{self.api_url}/search",
                json=payload,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()

            items = [STACItem(**feature) for feature in data.get("features", [])]

            return STACItemCollection(
                type=data.get("type", "FeatureCollection"),
                features=items,
                links=data.get("links", []),
                context=data.get("context"),
            )
        except Exception as e:
            logger.error(f"Search with geometry failed: {e}")
            raise

    async def get_item(self, collection_id: str, item_id: str) -> Optional[STACItem]:
        """Get a specific item (scene) by ID."""
        try:
            response = await self.client.get(
                f"{self.api_url}/collections/{collection_id}/items/{item_id}"
            )
            response.raise_for_status()
            return STACItem(**response.json())
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return None
            raise
        except Exception as e:
            logger.error(f"Failed to get item {collection_id}/{item_id}: {e}")
            raise
