from fastapi import APIRouter


router = APIRouter()

@router.get("/")
async def list_projects():
    """Lists all projects."""
    return {"message": "List of projects"}

@router.post("/")
async def create_project():
    """Creates a new project."""
    return {"message": "Project created"}