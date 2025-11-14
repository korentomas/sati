from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.api.v1.features.projects.manager import ProjectManager
from app.api.v1.features.projects.models import Layer, MapView, MetricsReport
from app.api.v1.features.projects.services import LayerManager

router = APIRouter()


# Dependency injection helpers
def get_project_manager() -> ProjectManager:
    """Get ProjectManager instance."""
    return ProjectManager()


def get_layer_manager() -> LayerManager:
    """Get LayerManager instance."""
    return LayerManager()


# ========== Request/Response Models ==========


class CreateProjectRequest(BaseModel):
    """Request model for creating a project."""

    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class AnalysisRequest(BaseModel):
    """Request model for analysis."""

    expression: str
    layer_ids: List[str]


class ExportRequest(BaseModel):
    """Request model for export."""

    format: str = "GeoJSON"
    layer_ids: Optional[List[str]] = None


class LayerUpdateRequest(BaseModel):
    """Request model for layer updates."""

    crs: Optional[str] = None
    visible: Optional[bool] = None
    opacity: Optional[float] = None


class AOISearchRequest(BaseModel):
    """Request model for AOI search."""

    bbox: List[float]
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    collections: Optional[List[str]] = None
    cloud_cover_max: Optional[float] = 100


# ========== Original Endpoints (Enhanced) ==========


@router.get("/")
async def list_projects(
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, Any]:
    """Lists all projects."""
    projects = project_manager.projects
    return {
        "total": len(projects),
        "projects": [{"id": pid, "data": pdata} for pid, pdata in projects.items()],
    }


@router.post("/")
async def create_project(
    request: CreateProjectRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, Any]:
    """Creates a new project."""
    from uuid import uuid4

    project_id = str(uuid4())
    project_data = {
        "name": request.name,
        "description": request.description,
        "metadata": request.metadata or {},
    }

    project_manager.create_project(project_id, project_data)

    return {
        "id": project_id,
        "message": "Project created successfully",
        "data": project_data,
    }


# ========== New UML-Aligned Endpoints ==========


@router.get("/{project_id}")
async def get_project(
    project_id: str, project_manager: ProjectManager = Depends(get_project_manager)
) -> Dict[str, Any]:
    """Get a specific project."""
    project = project_manager.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {"id": project_id, "data": project}


@router.delete("/{project_id}")
async def delete_project(
    project_id: str, project_manager: ProjectManager = Depends(get_project_manager)
) -> Dict[str, str]:
    """Delete a project."""
    project_manager.delete_project(project_id)
    return {"message": f"Project {project_id} deleted successfully"}


@router.post("/{project_id}/load-local")
async def load_local_data(
    project_id: str,
    file: UploadFile = File(...),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Layer:
    """Load local file data into project."""
    # Save uploaded file temporarily
    import tempfile

    with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    # Load the file
    layer = project_manager.load_local_data(tmp_path)

    # Add to project layers
    if project_id not in project_manager.layers:
        project_manager.layers[project_id] = []
    project_manager.layers[project_id].append(layer)

    return layer


@router.post("/{project_id}/search-import")
async def search_and_import_rasters(
    project_id: str,
    request: AOISearchRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> List[Layer]:
    """Search and import rasters for an AOI."""
    aoi = {"bbox": request.bbox}
    filters = {
        "date_from": request.date_from,
        "date_to": request.date_to,
        "collections": request.collections,
        "cloud_cover_max": request.cloud_cover_max,
    }

    layers = await project_manager.search_and_import_rasters(aoi, filters)

    # Add to project
    if project_id not in project_manager.layers:
        project_manager.layers[project_id] = []
    project_manager.layers[project_id].extend(layers)

    return layers


@router.get("/{project_id}/layers")
async def list_project_layers(
    project_id: str, project_manager: ProjectManager = Depends(get_project_manager)
) -> List[Layer]:
    """List all layers in a project."""
    layers = project_manager.layers.get(project_id, [])
    return layers


@router.post("/{project_id}/layers")
async def add_layer_to_project(
    project_id: str,
    layer: Layer,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Layer:
    """Add a layer to the project."""
    if project_id not in project_manager.layers:
        project_manager.layers[project_id] = []

    project_manager.layers[project_id].append(layer)
    return layer


@router.patch("/{project_id}/layers/{layer_id}")
async def update_layer(
    project_id: str,
    layer_id: str,
    updates: LayerUpdateRequest,
    layer_manager: LayerManager = Depends(get_layer_manager),
) -> Dict[str, str]:
    """Update layer properties."""
    if updates.crs:
        layer_manager.set_crs(layer_id, updates.crs)
    if updates.visible is not None:
        layer_manager.toggle_visibility(layer_id, updates.visible)
    if updates.opacity is not None:
        layer_manager.set_opacity(layer_id, updates.opacity)

    return {"message": f"Layer {layer_id} updated successfully"}


@router.delete("/{project_id}/layers/{layer_id}")
async def remove_layer(
    project_id: str,
    layer_id: str,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, str]:
    """Remove a layer from the project."""
    if project_id in project_manager.layers:
        project_manager.layers[project_id] = [
            layer
            for layer in project_manager.layers[project_id]
            if layer.id != layer_id
        ]

    return {"message": f"Layer {layer_id} removed successfully"}


@router.post("/{project_id}/layers/reorder")
async def reorder_layers(
    project_id: str,
    order: List[str] = Body(...),
    layer_manager: LayerManager = Depends(get_layer_manager),
) -> Dict[str, str]:
    """Reorder layers in the project."""
    layer_manager.reorder_layers(order)
    return {"message": "Layers reordered successfully"}


@router.get("/{project_id}/visualize")
async def visualize_project(
    project_id: str, project_manager: ProjectManager = Depends(get_project_manager)
) -> MapView:
    """Get map visualization for the project."""
    # Set current project context
    if project_id not in project_manager.projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return project_manager.visualize_layers()


@router.post("/{project_id}/analysis")
async def perform_analysis(
    project_id: str,
    request: AnalysisRequest,
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Layer:
    """Perform analysis on project layers."""
    # Get specified layers
    project_layers = project_manager.layers.get(project_id, [])
    selected_layers = [
        layer for layer in project_layers if layer.id in request.layer_ids
    ]

    if not selected_layers:
        raise HTTPException(status_code=404, detail="No matching layers found")

    # Perform analysis
    result_layer = await project_manager.perform_analysis(
        request.expression, selected_layers
    )

    # Add result to project
    project_manager.layers[project_id].append(result_layer)

    return result_layer


@router.post("/{project_id}/export")
async def export_project(
    project_id: str,
    output_path: str = Body(...),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, str]:
    """Export project to a file."""
    if project_id not in project_manager.projects:
        raise HTTPException(status_code=404, detail="Project not found")

    project_manager.export_project(output_path)

    return {"message": "Project exported successfully", "path": output_path}


@router.post("/import")
async def import_project(
    project_path: str = Body(...),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Dict[str, Any]:
    """Import a project from a file."""
    project_manager.load_project(project_path)

    return {
        "message": "Project imported successfully",
        "projects": len(project_manager.projects),
        "path": project_path,
    }


@router.get("/{project_id}/metrics")
async def get_project_metrics(
    project_id: str, project_manager: ProjectManager = Depends(get_project_manager)
) -> MetricsReport:
    """Get metrics for the project."""
    if project_id not in project_manager.projects:
        raise HTTPException(status_code=404, detail="Project not found")

    return project_manager.collect_metrics()


@router.post("/{project_id}/mosaic")
async def create_mosaic(
    project_id: str,
    scene_ids: List[str] = Body(...),
    options: Dict[str, Any] = Body(default={}),
    project_manager: ProjectManager = Depends(get_project_manager),
) -> Layer:
    """Create a mosaic from multiple scenes."""
    mosaic_layer = project_manager.create_mosaic(scene_ids, options)

    # Add to project
    if project_id not in project_manager.layers:
        project_manager.layers[project_id] = []
    project_manager.layers[project_id].append(mosaic_layer)

    return mosaic_layer
