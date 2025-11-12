from typing import Dict, Optional, Any


class ProjectManager:
    """Manages user projects."""

    def __init__(self) -> None:
        self.projects: Dict[str, Dict[str, Any]] = {}

    def create_project(self, project_id: str, data: Dict[str, Any]) -> None:
        """Creates a new project."""
        self.projects[project_id] = data

    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a project."""
        return self.projects.get(project_id)

    def delete_project(self, project_id: str) -> None:
        """Deletes a project."""
        if project_id in self.projects:
            del self.projects[project_id]
