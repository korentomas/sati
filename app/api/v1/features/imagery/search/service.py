"""Service layer for imagery search functionality."""

from datetime import datetime
from typing import List, Optional

from app.api.v1.features.imagery.search.schemas import (
    CollectionInfo,
    SceneProperties,
    SceneResponse,
    SearchRequest,
    SearchResponse,
    GeoJSONGeometry,
)
from app.api.v1.features.imagery.stac.client import STACClient
from app.core.logging import logger


class SearchService:
    """Service for searching satellite imagery."""

    def __init__(self):
        """Initialize search service."""
        self.stac_client = STACClient()

    async def list_collections(self) -> List[CollectionInfo]:
        """List all available satellite data collections."""
        try:
            async with STACClient() as client:
                collections = await client.list_collections()

                # Convert to our response format
                result = []
                for coll in collections:
                    info = CollectionInfo(
                        id=coll.id,
                        title=coll.title or coll.id,
                        description=coll.description,
                        temporal_extent=coll.temporal_extent,
                    )

                    # Extract spatial extent if available
                    if "spatial" in coll.extent:
                        bbox = coll.extent["spatial"].get("bbox", [[]])[0]
                        if bbox:
                            info.spatial_extent = bbox

                    result.append(info)

                return result
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise

    async def search_imagery(self, request: SearchRequest) -> SearchResponse:
        """Search for satellite imagery based on criteria."""
        try:
            async with STACClient() as client:
                # Perform search based on geometry or bbox
                if request.geometry:
                    results = await client.search_with_geometry(
                        geometry=request.geometry.dict(),
                        collections=request.collections,
                        datetime=request.datetime_range,
                        limit=request.limit,
                        cloud_cover_max=request.cloud_cover_max,
                    )
                else:
                    # Use bbox search
                    query = None
                    if request.cloud_cover_max < 100:
                        query = {"eo:cloud_cover": {"lt": request.cloud_cover_max}}

                    results = await client.search(
                        collections=request.collections,
                        bbox=request.bbox,
                        datetime=request.datetime_range,
                        limit=request.limit,
                        query=query,
                    )

                # Convert STAC items to our response format
                scenes = []
                for item in results.features:
                    scene = SceneResponse(
                        id=item.id,
                        collection=item.collection,
                        bbox=item.bbox,
                        geometry=GeoJSONGeometry(**item.geometry),
                        properties=SceneProperties(
                            datetime=item.datetime or datetime.now(),
                            cloud_cover=item.cloud_cover,
                            platform=item.properties.get("platform"),
                            instrument=item.properties.get("instruments", [None])[0]
                            if item.properties.get("instruments")
                            else None,
                            gsd=item.properties.get("gsd"),
                        ),
                        thumbnail_url=item.thumbnail_url,
                        assets={
                            name: {"href": asset.href, "type": asset.type}
                            for name, asset in item.assets.items()
                        },
                    )
                    scenes.append(scene)

                # Build response
                response = SearchResponse(
                    total=results.context.get("matched", len(scenes))
                    if results.context
                    else len(scenes),
                    returned=len(scenes),
                    scenes=scenes,
                    next_token=results.next_link,
                )

                return response
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise

    async def get_scene(
        self, collection_id: str, scene_id: str
    ) -> Optional[SceneResponse]:
        """Get details of a specific scene."""
        try:
            async with STACClient() as client:
                item = await client.get_item(collection_id, scene_id)

                if not item:
                    return None

                return SceneResponse(
                    id=item.id,
                    collection=item.collection,
                    bbox=item.bbox,
                    geometry=GeoJSONGeometry(**item.geometry),
                    properties=SceneProperties(
                        datetime=item.datetime or datetime.now(),
                        cloud_cover=item.cloud_cover,
                        platform=item.properties.get("platform"),
                        instrument=item.properties.get("instruments", [None])[0]
                        if item.properties.get("instruments")
                        else None,
                        gsd=item.properties.get("gsd"),
                    ),
                    thumbnail_url=item.thumbnail_url,
                    assets={
                        name: {"href": asset.href, "type": asset.type}
                        for name, asset in item.assets.items()
                    },
                )
        except Exception as e:
            logger.error(f"Failed to get scene {collection_id}/{scene_id}: {e}")
            raise