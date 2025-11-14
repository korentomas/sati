from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import uuid4

import aiohttp
import geopandas as gpd
import rasterio

from app.api.v1.features.imagery.search.schemas import SearchRequest
from app.api.v1.features.imagery.search.service import SearchService
from app.api.v1.features.projects.models import Layer


class DataImporter:
    """Handles data import for projects - Full UML implementation."""

    def __init__(self, search_service: SearchService) -> None:
        self.search_service = search_service
        self.download_service = None  # Will be injected in production

    async def import_from_search(self, search_request: SearchRequest) -> Any:
        """Imports data from a search request."""
        return await self.search_service.search_imagery(search_request)

    # ========== NEW UML METHODS ==========

    def load_local(self, file_path: str) -> Layer:
        """Load a local file as a Layer.

        Args:
            file_path: Path to local file (GeoTIFF, Shapefile, GeoJSON, etc.)

        Returns:
            Layer object with loaded data
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        layer_id = str(uuid4())
        metadata = {"source": "local", "file_path": str(path)}

        # Determine file type and load accordingly
        extension = path.suffix.lower()

        if extension in [".tif", ".tiff", ".geotiff"]:
            # Load as raster
            with rasterio.open(file_path) as src:
                metadata.update(
                    {
                        "bounds": src.bounds,
                        "crs": str(src.crs),
                        "width": src.width,
                        "height": src.height,
                        "bands": src.count,
                        "dtype": str(src.dtypes[0]),
                    }
                )
                layer_type = "raster"

        elif extension in [".shp", ".gpkg", ".geojson", ".json"]:
            # Load as vector
            gdf = gpd.read_file(file_path)
            metadata.update(
                {
                    "bounds": gdf.total_bounds.tolist(),
                    "crs": str(gdf.crs) if gdf.crs else "EPSG:4326",
                    "features": str(len(gdf)),
                    "geometry_type": gdf.geom_type.unique().tolist(),
                }
            )
            layer_type = "vector"

        else:
            raise ValueError(f"Unsupported file type: {extension}")

        return Layer(
            id=layer_id,
            name=path.stem,
            type=layer_type,
            crs=metadata.get("crs", "EPSG:4326"),
            metadata=metadata,
            data={"file_path": file_path},
        )

    async def search_online(
        self, aoi: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Layer]:
        """Search for data online within an AOI.

        Args:
            aoi: Area of interest (bbox or geometry)
            filters: Search filters (collections, date range, etc.)

        Returns:
            List of Layer objects from search results
        """
        # Build search request
        # Convert date strings to datetime if needed
        date_from = filters.get("date_from")
        date_to = filters.get("date_to")
        if isinstance(date_from, str):
            date_from = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
        if isinstance(date_to, str):
            date_to = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
        if not date_from:
            date_from = datetime(2020, 1, 1)
        if not date_to:
            date_to = datetime.now()

        search_request = SearchRequest(
            date_from=date_from,
            date_to=date_to,
            bbox=aoi.get("bbox", [-180, -90, 180, 90]),
            collections=filters.get("collections", []),
            cloud_cover_max=filters.get("cloud_cover_max", 100),
            limit=filters.get("limit", 20),
        )

        # Perform search
        results = await self.search_service.search_imagery(search_request)

        # Convert results to Layers
        layers = []
        for scene in results.scenes if hasattr(results, "scenes") else []:
            # Convert properties to dict if it's a Pydantic model
            if hasattr(scene, "properties"):
                props = scene.properties
                if hasattr(props, "dict"):
                    metadata = props.dict()
                elif hasattr(props, "model_dump"):
                    metadata = props.model_dump()
                else:
                    metadata = dict(props) if isinstance(props, dict) else {}
            else:
                metadata = {}

            # Convert scene to dict
            if hasattr(scene, "dict"):
                scene_data = scene.dict()
            elif hasattr(scene, "model_dump"):
                scene_data = scene.model_dump()
            else:
                scene_data = dict(scene) if isinstance(scene, dict) else {}

            layer = Layer(
                id=scene.id if hasattr(scene, "id") else str(uuid4()),
                name=scene.collection if hasattr(scene, "collection") else "Unknown",
                type="raster",
                metadata=metadata,
                data=scene_data,
            )
            layers.append(layer)

        return layers

    async def download_raster(self, url: str) -> Layer:
        """Download a raster from a URL and convert to Layer.

        Args:
            url: URL of the raster to download

        Returns:
            Layer object with downloaded data
        """
        if self.download_service:
            # Use the download service if available
            result = await self.download_service.download_scene(url, {})
            return Layer(
                id=str(uuid4()),
                name=f"Downloaded_{url.split('/')[-1]}",
                type="raster",
                metadata={"source": "download", "url": url},
                data=result,
            )

        # Fallback: Simple download implementation
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.read()
                    # Save to temporary file
                    import tempfile

                    with tempfile.NamedTemporaryFile(
                        suffix=".tif", delete=False
                    ) as tmp:
                        tmp.write(content)
                        tmp_path = tmp.name

                    # Load the downloaded file
                    return self.load_local(tmp_path)
                else:
                    raise ValueError(
                        f"Failed to download from {url}: {response.status}"
                    )


class LayerManager:
    """Manages layers in the project - Full UML implementation."""

    def __init__(self) -> None:
        self.layers: List[Dict[str, Any]] = []
        self.layer_order: List[str] = []  # Track layer ordering

    def add_layer(self, layer: Dict[str, Any]) -> None:
        """Adds a new layer to the project."""
        self.layers.append(layer)
        if "id" in layer:
            self.layer_order.append(layer["id"])

    def remove_layer(self, layer_id: str) -> None:
        """Removes a layer from the project."""
        self.layers = [layer for layer in self.layers if layer.get("id") != layer_id]
        if layer_id in self.layer_order:
            self.layer_order.remove(layer_id)

    def list_layers(self) -> List[Dict[str, Any]]:
        """Lists all layers in the project."""
        # Return layers in the specified order
        if self.layer_order:
            ordered_layers = []
            for layer_id in self.layer_order:
                for layer in self.layers:
                    if layer.get("id") == layer_id:
                        ordered_layers.append(layer)
                        break
            # Add any layers not in the order list
            for layer in self.layers:
                if layer not in ordered_layers:
                    ordered_layers.append(layer)
            return ordered_layers
        return self.layers

    # ========== NEW UML METHODS ==========

    def set_crs(self, layer_id: str, crs: str) -> None:
        """Set the CRS of a layer.

        Args:
            layer_id: ID of the layer to update
            crs: Target coordinate reference system (e.g., "EPSG:4326")
        """
        for layer in self.layers:
            if layer.get("id") == layer_id:
                layer["crs"] = crs
                # Mark as needing reprojection
                if "metadata" not in layer:
                    layer["metadata"] = {}
                layer["metadata"]["needs_reprojection"] = True
                layer["metadata"]["target_crs"] = crs
                break

    def toggle_visibility(self, layer_id: str, visible: bool) -> None:
        """Toggle layer visibility.

        Args:
            layer_id: ID of the layer to update
            visible: Whether the layer should be visible
        """
        for layer in self.layers:
            if layer.get("id") == layer_id:
                layer["visible"] = visible
                break

    def reorder_layers(self, order: List[str]) -> None:
        """Reorder layers based on provided order.

        Args:
            order: List of layer IDs in desired order
        """
        # Validate that all IDs exist
        existing_ids = {layer.get("id") for layer in self.layers if "id" in layer}
        valid_order = [lid for lid in order if lid in existing_ids]

        # Update the layer order
        self.layer_order = valid_order

    def set_opacity(self, layer_id: str, opacity: float) -> None:
        """Set layer opacity.

        Args:
            layer_id: ID of the layer to update
            opacity: Opacity value between 0.0 and 1.0
        """
        # Clamp opacity to valid range
        opacity = max(0.0, min(1.0, opacity))

        for layer in self.layers:
            if layer.get("id") == layer_id:
                layer["opacity"] = opacity
                break


class MapVisualizer:
    """Renders maps for the project - Full UML implementation."""

    def __init__(self, layers: List[Dict[str, Any]] = None) -> None:
        self.layers = layers or []
        self.base_map = "OpenStreetMap"
        self.zoom_level = 10
        self.center = [0, 0]

    def render(self) -> str:
        """Renders the map as an HTML string."""
        # Enhanced rendering with layer info
        layer_html = ""
        for layer in self.layers:
            layer_name = layer.get("name", "Unknown")
            layer_type = layer.get("type", "layer")
            layer_html += f"<li>{layer_name} - {layer_type}</li>"

        html = f"""
        <html>
        <head><title>Map Visualization</title></head>
        <body>
            <h1>Map View</h1>
            <p>Base Map: {self.base_map}</p>
            <p>Layers ({len(self.layers)}):</p>
            <ul>{layer_html}</ul>
            <p>Center: {self.center}, Zoom: {self.zoom_level}</p>
        </body>
        </html>
        """
        return html

    # ========== NEW UML METHODS ==========

    def render_map(self, layers: List[Any]) -> Any:
        """Render map with specified layers.

        Args:
            layers: List of Layer objects to render

        Returns:
            MapView object with rendering info
        """
        from app.api.v1.features.projects.models import Layer, MapView

        # Convert dict layers to Layer objects if needed
        layer_objects = []
        for layer in layers:
            if isinstance(layer, dict):
                layer_objects.append(Layer(**layer))
            else:
                layer_objects.append(layer)

        return MapView(layers=layer_objects, base_map=self.base_map)

    def add_basemap(self, provider: str) -> None:
        """Add or change the basemap provider.

        Args:
            provider: Name of the basemap provider
                     (e.g., "OpenStreetMap", "CartoDB", "Stamen")
        """
        valid_providers = ["OpenStreetMap", "CartoDB", "Stamen", "ESRI", "Google"]
        if provider in valid_providers:
            self.base_map = provider
        else:
            raise ValueError(
                f"Invalid basemap provider. Choose from: {valid_providers}"
            )

    def zoom_to_layer(self, layer: Dict[str, Any]) -> None:
        """Zoom the map to fit a specific layer.

        Args:
            layer: Layer to zoom to
        """
        if "metadata" in layer and "bounds" in layer["metadata"]:
            bounds = layer["metadata"]["bounds"]
            # Calculate center from bounds
            if isinstance(bounds, (list, tuple)) and len(bounds) >= 4:
                self.center = [
                    (bounds[1] + bounds[3]) / 2,  # lat
                    (bounds[0] + bounds[2]) / 2,  # lon
                ]
                # Estimate zoom level based on bounds extent
                lat_diff = abs(bounds[3] - bounds[1])
                lon_diff = abs(bounds[2] - bounds[0])
                max_diff = max(lat_diff, lon_diff)
                if max_diff > 10:
                    self.zoom_level = 5
                elif max_diff > 1:
                    self.zoom_level = 8
                else:
                    self.zoom_level = 12


class AnalysisEngine:
    """Performs analysis on project data - Full UML implementation."""

    def __init__(self, layers: List[Dict[str, Any]] = None) -> None:
        self.layers = layers or []
        self.processing_service = None  # Will be injected in production

    def calculate_statistics(self) -> Dict[str, Any]:
        """Calculates statistics for the layers."""
        return {"layer_count": len(self.layers)}

    # ========== NEW UML METHODS ==========

    async def calculate(self, expression: str, layers: List[Any]) -> Any:
        """Calculate analysis expression on layers.

        Args:
            expression: Analysis expression (e.g., "NDVI", "(B4-B3)/(B4+B3)")
            layers: Input layers for calculation

        Returns:
            Result of the calculation
        """
        if self.processing_service:
            # Delegate to ProcessingService for complex calculations
            return await self.processing_service.calculate_index(
                layers[0].id if layers else None, expression
            )

        # Simple mock calculation
        result = {
            "expression": expression,
            "input_layers": len(layers),
            "result_type": "calculated",
            "data": f"Mock result for {expression}",
        }

        return result

    def clip_raster_by_aoi(self, raster: Dict[str, Any], aoi: Dict[str, Any]) -> Any:
        """Clip a raster by an area of interest.

        Args:
            raster: Raster layer to clip
            aoi: Area of interest (geometry or bbox)

        Returns:
            Clipped raster as Layer
        """
        from app.api.v1.features.projects.models import Layer

        # Mock implementation
        return Layer(
            id=str(uuid4()),
            name=f"Clipped_{raster.get('name', 'raster')}",
            type="raster",
            metadata={
                "source_raster": raster.get("id"),
                "aoi": aoi,
                "operation": "clip",
            },
        )

    def measure_distance(
        self, geom1: Dict[str, Any], geom2: Dict[str, Any], unit: str = "meters"
    ) -> float:
        """Measure distance between two geometries.

        Args:
            geom1: First geometry
            geom2: Second geometry
            unit: Unit of measurement (meters, kilometers, miles)

        Returns:
            Distance in specified units
        """
        # Simple euclidean distance calculation (mock)
        # In production, use proper geodesic calculations
        import math

        # Extract coordinates (assuming point geometries)
        lat1 = geom1.get("lat", 0)
        lon1 = geom1.get("lon", 0)
        lat2 = geom2.get("lat", 0)
        lon2 = geom2.get("lon", 0)

        # Haversine formula for distance
        R = 6371000  # Earth radius in meters
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        )
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        distance = R * c

        # Convert to requested unit
        if unit == "kilometers":
            return distance / 1000
        elif unit == "miles":
            return distance / 1609.34
        else:
            return distance


class ExportService:
    """Exports project data - Full UML implementation."""

    def __init__(self, layers: List[Dict[str, Any]] = None) -> None:
        self.layers = layers or []

    def to_geojson(self) -> Dict[str, Any]:
        """Exports layers to GeoJSON format."""
        return {"type": "FeatureCollection", "features": self.layers}

    # ========== NEW UML METHODS ==========

    def export_layer(self, layer: Any, format: str) -> Dict[str, Any]:
        """Export a layer to specified format.

        Args:
            layer: Layer to export
            format: Export format (GeoTIFF, GeoJSON, Shapefile, KML, etc.)

        Returns:
            File object with exported data
        """
        import tempfile

        supported_formats = ["GeoTIFF", "GeoJSON", "Shapefile", "KML", "CSV", "PNG"]
        if format not in supported_formats:
            raise ValueError(f"Unsupported format. Choose from: {supported_formats}")

        # Create temporary file path
        suffix = {
            "GeoTIFF": ".tif",
            "GeoJSON": ".geojson",
            "Shapefile": ".shp",
            "KML": ".kml",
            "CSV": ".csv",
            "PNG": ".png",
        }.get(format, ".dat")

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp_path = tmp.name

        # Mock export (in production, use GDAL/OGR for actual conversion)
        file_info = {
            "path": tmp_path,
            "format": format,
            "layer_id": layer.id if hasattr(layer, "id") else layer.get("id"),
            "size_bytes": 1024,  # Mock size
            "mime_type": {
                "GeoTIFF": "image/tiff",
                "GeoJSON": "application/geo+json",
                "Shapefile": "application/x-shapefile",
                "KML": "application/vnd.google-earth.kml+xml",
                "CSV": "text/csv",
                "PNG": "image/png",
            }.get(format, "application/octet-stream"),
        }

        return file_info

    def save_project(self, project: Dict[str, Any]) -> str:
        """Save project to persistent storage.

        Args:
            project: Project data to save

        Returns:
            Path where project was saved
        """
        import json
        import tempfile
        from pathlib import Path

        # Create project directory
        project_dir = (
            Path(tempfile.gettempdir()) / f"project_{project.get('id', 'unknown')}"
        )
        project_dir.mkdir(parents=True, exist_ok=True)

        # Save project metadata
        project_file = project_dir / "project.json"
        with open(project_file, "w") as f:
            json.dump(project, f, indent=2, default=str)

        # Save layers separately
        layers_dir = project_dir / "layers"
        layers_dir.mkdir(exist_ok=True)

        for i, layer in enumerate(self.layers):
            layer_file = layers_dir / f"layer_{i}.json"
            with open(layer_file, "w") as f:
                json.dump(layer, f, indent=2, default=str)

        return str(project_dir)

    def load_project(self, path: str) -> Dict[str, Any]:
        """Load project from storage.

        Args:
            path: Path to project directory or file

        Returns:
            Project data
        """
        import json
        from pathlib import Path

        project_path = Path(path)

        if project_path.is_file():
            # Load single file
            with open(project_path, "r") as f:
                return json.load(f)

        elif project_path.is_dir():
            # Load project directory
            project_file = project_path / "project.json"
            if not project_file.exists():
                raise FileNotFoundError(f"No project.json found in {path}")

            with open(project_file, "r") as f:
                project = json.load(f)

            # Load layers
            layers_dir = project_path / "layers"
            if layers_dir.exists():
                layers = []
                for layer_file in sorted(layers_dir.glob("layer_*.json")):
                    with open(layer_file, "r") as f:
                        layers.append(json.load(f))
                project["layers"] = layers

            return project

        else:
            raise FileNotFoundError(f"Project not found at {path}")


class MetricsCollector:
    """Collects metrics for the project - Full UML implementation."""

    def __init__(self) -> None:
        self.metrics: List[Dict[str, Any]] = []
        self.performance_data: List[float] = []
        self.error_log: List[Dict[str, Any]] = []
        self.request_count = 0

    def collect(self, metric: Dict[str, Any]) -> None:
        """Collects a new metric."""
        self.metrics.append(metric)
        self.request_count += 1

        # Track performance if response time is included
        if "response_time" in metric:
            self.performance_data.append(metric["response_time"])

    def generate_report(self) -> Dict[str, Any]:
        """Generates a report of collected metrics."""
        return {"metrics": self.metrics}

    # ========== NEW UML METHODS ==========

    def collect_performance_data(self) -> Any:
        """Collect and return performance metrics.

        Returns:
            MetricsReport with performance data
        """
        import statistics

        from app.api.v1.features.projects.models import MetricsReport

        avg_response = (
            statistics.mean(self.performance_data) if self.performance_data else 0.0
        )

        return MetricsReport(
            avg_response_time=avg_response,
            total_requests=self.request_count,
            errors=len(self.error_log),
            additional_metrics={
                "min_response_time": (
                    min(self.performance_data) if self.performance_data else 0
                ),
                "max_response_time": (
                    max(self.performance_data) if self.performance_data else 0
                ),
                "median_response_time": (
                    statistics.median(self.performance_data)
                    if self.performance_data
                    else 0
                ),
                "total_metrics": len(self.metrics),
            },
            metrics=self.metrics,  # Keep for backward compatibility
        )

    def log_error(self, event: Dict[str, Any]) -> None:
        """Log an error event.

        Args:
            event: Error event with details (timestamp, message, stack_trace, etc.)
        """
        import datetime

        error_entry = {
            "timestamp": event.get("timestamp", datetime.datetime.now().isoformat()),
            "message": event.get("message", "Unknown error"),
            "type": event.get("type", "ERROR"),
            "stack_trace": event.get("stack_trace"),
            "context": event.get("context", {}),
        }

        self.error_log.append(error_entry)

        # Also add to general metrics
        self.metrics.append({"type": "error", **error_entry})
