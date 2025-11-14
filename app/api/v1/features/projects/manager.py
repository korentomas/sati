import json
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import geopandas as gpd
import rasterio

from app.api.v1.features.projects.models import Layer, MapView, MetricsReport


class ProjectManager:
    """Manages user projects - Full UML implementation."""

    def __init__(self) -> None:
        self.projects: Dict[str, Dict[str, Any]] = {}
        self.layers: Dict[str, List[Layer]] = {}  # Project layers storage
        self.metrics: Dict[str, List[Dict]] = {}  # Project metrics storage

        # Initialize service dependencies (will be injected in production)
        self.data_importer = None
        self.layer_manager = None
        self.map_visualizer = None
        self.analysis_engine = None
        self.export_service = None
        self.metrics_collector = None

    def create_project(self, project_id: str, data: Dict[str, Any]) -> None:
        """Creates a new project."""
        self.projects[project_id] = data
        self.layers[project_id] = []
        self.metrics[project_id] = []

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a project."""
        return self.projects.get(project_id)

    def delete_project(self, project_id: str) -> None:
        """Deletes a project."""
        if project_id in self.projects:
            del self.projects[project_id]
            if project_id in self.layers:
                del self.layers[project_id]
            if project_id in self.metrics:
                del self.metrics[project_id]

    # ========== NEW UML METHODS ==========

    def load_local_data(self, file_path: str) -> Layer:
        """Load local raster or vector data and convert to Layer.

        Args:
            file_path: Path to local file (GeoTIFF, Shapefile, etc.)

        Returns:
            Layer object with loaded data
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        layer_id = str(uuid4())
        layer_type = "raster"
        metadata = {"source": "local", "file_path": str(path)}

        try:
            # Try loading as raster first
            with rasterio.open(file_path) as src:
                metadata.update(
                    {
                        "bounds": src.bounds,
                        "crs": str(src.crs),
                        "width": src.width,
                        "height": src.height,
                        "bands": src.count,
                    }
                )
                layer_type = "raster"
        except (rasterio.errors.RasterioIOError, Exception):
            try:
                # Try loading as vector
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
            except Exception as e:
                raise ValueError(f"Unable to load file as raster or vector: {e}")

        return Layer(
            id=layer_id,
            name=path.stem,
            type=layer_type,
            crs=metadata.get("crs", "EPSG:4326"),
            metadata=metadata,
            data={"file_path": file_path},
        )

    async def search_and_import_rasters(
        self, aoi: Dict[str, Any], filters: Dict[str, Any]
    ) -> List[Layer]:
        """Search for rasters in an AOI and import them as Layers.

        Args:
            aoi: Area of interest (bbox or geometry)
            filters: Search filters (date range, cloud cover, collections, etc.)

        Returns:
            List of Layer objects from search results
        """
        if not self.data_importer:
            # Mock implementation when service not available
            return [
                Layer(
                    id=str(uuid4()),
                    name=f"Scene_{i}",
                    type="raster",
                    metadata={"aoi": aoi, "filters": filters, "mock": True},
                )
                for i in range(3)  # Return 3 mock layers
            ]

        # Use DataImporter to search and convert to Layers
        results = await self.data_importer.search_online(aoi, filters)

        layers = []
        for scene in results:
            layers.append(
                Layer(
                    id=scene.get("id", str(uuid4())),
                    name=scene.get("collection", "Unknown"),
                    type="raster",
                    metadata=scene.get("properties", {}),
                    data=scene,
                )
            )

        return layers

    def visualize_layers(self) -> MapView:
        """Create a map view with all current layers.

        Returns:
            MapView object with configured layers
        """
        # Get all layers from the current project
        current_project_id = next(iter(self.projects.keys())) if self.projects else None

        if not current_project_id or current_project_id not in self.layers:
            # Return empty map view
            return MapView(layers=[], base_map="OpenStreetMap")

        layers = self.layers[current_project_id]

        # Filter only visible layers
        visible_layers = [layer for layer in layers if layer.visible]

        return MapView(
            layers=visible_layers, base_map="OpenStreetMap"  # Could be configurable
        )

    async def perform_analysis(self, expression: str, layers: List[Layer]) -> Layer:
        """Perform analysis on layers using an expression.

        Args:
            expression: Analysis expression (e.g., "NDVI", "B4-B3/B4+B3")
            layers: Input layers for analysis

        Returns:
            New Layer with analysis results
        """
        if not self.analysis_engine:
            # Mock implementation
            return Layer(
                id=str(uuid4()),
                name=f"Analysis: {expression[:20]}",
                type="processed",
                metadata={
                    "expression": expression,
                    "source_layers": [layer.id for layer in layers],
                    "mock": True,
                },
            )

        # Delegate to AnalysisEngine
        result = await self.analysis_engine.calculate(expression, layers)

        return Layer(
            id=str(uuid4()),
            name=f"Analysis: {expression[:20]}",
            type="processed",
            metadata={
                "expression": expression,
                "source_layers": [layer.id for layer in layers],
            },
            data=result,
        )

    def export_project(self, output_path: str) -> None:
        """Export project to a file.

        Args:
            output_path: Path where project will be saved
        """
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Prepare project data for export
        export_data = {
            "projects": self.projects,
            "layers": {
                project_id: [layer.dict() for layer in layers]
                for project_id, layers in self.layers.items()
            },
            "metrics": self.metrics,
            "version": "1.0.0",
        }

        # Save as JSON
        with open(path, "w") as f:
            json.dump(export_data, f, indent=2, default=str)

    def load_project(self, project_path: str) -> None:
        """Load project from a file.

        Args:
            project_path: Path to project file
        """
        path = Path(project_path)
        if not path.exists():
            raise FileNotFoundError(f"Project file not found: {project_path}")

        with open(path, "r") as f:
            import_data = json.load(f)

        # Restore project data
        self.projects = import_data.get("projects", {})
        self.metrics = import_data.get("metrics", {})

        # Restore layers
        self.layers = {}
        for project_id, layers_data in import_data.get("layers", {}).items():
            self.layers[project_id] = [
                Layer(**layer_data) for layer_data in layers_data
            ]

    def collect_metrics(self) -> MetricsReport:
        """Collect and return project metrics.

        Returns:
            MetricsReport with aggregated metrics
        """
        if not self.metrics_collector:
            # Generate mock metrics
            return MetricsReport(
                avg_response_time=125.5,
                total_requests=42,
                errors=2,
                additional_metrics={
                    "projects_count": len(self.projects),
                    "total_layers": sum(len(layers) for layers in self.layers.values()),
                },
            )

        # Delegate to MetricsCollector
        return self.metrics_collector.collect_performance_data()

    def create_mosaic(self, scene_ids: List[str], options: Dict[str, Any]) -> Layer:
        """Create a mosaic from multiple scenes.

        Args:
            scene_ids: List of scene IDs to mosaic
            options: Mosaic options (method, resolution, etc.)

        Returns:
            Layer containing the mosaic
        """
        # This would delegate to MosaicService in production
        return Layer(
            id=str(uuid4()),
            name=f"Mosaic_{len(scene_ids)}_scenes",
            type="composite",
            metadata={"scene_ids": scene_ids, "options": options, "mock": True},
        )
