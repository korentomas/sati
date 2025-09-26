"""STAC data models for imagery feature."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class STACLink(BaseModel):
    """STAC Link object."""

    href: str
    rel: str
    type: Optional[str] = None
    title: Optional[str] = None


class STACAsset(BaseModel):
    """STAC Asset object."""

    href: str
    title: Optional[str] = None
    type: Optional[str] = None
    roles: List[str] = Field(default_factory=list)


class STACCollection(BaseModel):
    """STAC Collection object."""

    id: str
    title: Optional[str] = None
    description: Optional[str] = None
    extent: Dict[str, Any] = Field(default_factory=dict)
    summaries: Dict[str, Any] = Field(default_factory=dict)
    links: List[STACLink] = Field(default_factory=list)

    @property
    def temporal_extent(self) -> Optional[List[str]]:
        """Get temporal extent from collection."""
        if "temporal" in self.extent:
            interval = self.extent["temporal"].get("interval", [[None, None]])[0]
            return interval
        return None


class STACItem(BaseModel):
    """STAC Item (Scene) object."""

    id: str
    collection: str
    geometry: Dict[str, Any]
    bbox: List[float]
    properties: Dict[str, Any]
    assets: Dict[str, STACAsset] = Field(default_factory=dict)
    links: List[STACLink] = Field(default_factory=list)

    @property
    def datetime(self) -> Optional[datetime]:
        """Get datetime from properties."""
        dt_str = self.properties.get("datetime")
        if dt_str:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return None

    @property
    def cloud_cover(self) -> Optional[float]:
        """Get cloud cover percentage."""
        return self.properties.get("eo:cloud_cover")

    @property
    def thumbnail_url(self) -> Optional[str]:
        """Get thumbnail URL if available."""
        if "thumbnail" in self.assets:
            return self.assets["thumbnail"].href
        return None


class STACItemCollection(BaseModel):
    """STAC Item Collection (search results)."""

    type: str = "FeatureCollection"
    features: List[STACItem] = Field(default_factory=list)
    links: List[STACLink] = Field(default_factory=list)
    context: Optional[Dict[str, Any]] = None

    @property
    def next_link(self) -> Optional[str]:
        """Get next page link if available."""
        for link in self.links:
            if link.rel == "next":
                return link.href
        return None