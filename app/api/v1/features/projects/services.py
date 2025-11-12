from app.api.v1.features.imagery.search.service import SearchService

class DataImporter:
    """Handles data import for projects."""
    def __init__(self, search_service: SearchService):
        self.search_service = search_service

    async def import_from_search(self, search_request: dict):
        """Imports data from a search request."""
        return await self.search_service.search_imagery(search_request)
class LayerManager:
    """Manages layers in the project."""
    def __init__(self):
        self.layers = []

    def add_layer(self, layer: dict):
        """Adds a new layer to the project."""
        self.layers.append(layer)

    def remove_layer(self, layer_id: str):
        """Removes a layer from the project."""
        self.layers = [layer for layer in self.layers if layer["id"] != layer_id]

    def list_layers(self) -> list:
        """Lists all layers in the project."""
        return self.layers
class MapVisualizer:
    """Renders maps for the project."""
    def __init__(self, layers: list):
        self.layers = layers

    def render(self) -> str:
        """Renders the map as an HTML string."""
        return f"<html><body><h1>Map</h1><p>Layers: {self.layers}</p></body></html>"
class AnalysisEngine:
    """Performs analysis on project data."""
    def __init__(self, layers: list):
        self.layers = layers

    def calculate_statistics(self) -> dict:
        """Calculates statistics for the layers."""
        return {"layer_count": len(self.layers)}
class ExportService:
    """Exports project data."""
    def __init__(self, layers: list):
        self.layers = layers

    def to_geojson(self) -> dict:
        """Exports layers to GeoJSON format."""
        return {"type": "FeatureCollection", "features": self.layers}
class MetricsCollector:
    """Collects metrics for the project."""
    def __init__(self):
        self.metrics = []

    def collect(self, metric: dict):
        """Collects a new metric."""
        self.metrics.append(metric)

    def generate_report(self) -> dict:
        """Generates a report of collected metrics."""
        return {"metrics": self.metrics}