from typing import Dict

from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def list_projects() -> Dict[str, str]:
    """Lists all projects."""
    return {"message": "List of projects"}


@router.post("/")
async def create_project() -> Dict[str, str]:
    """Creates a new project."""
    return {"message": "Project created"}
