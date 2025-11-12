class ProjectManager:
    """Manages user projects."""
    def __init__(self):
        self.projects = {}

    def create_project(self, project_id: str, data: dict):
        """Creates a new project."""
        self.projects[project_id] = data

    def get_project(self, project_id: str) -> dict:
        """Retrieves a project."""
        return self.projects.get(project_id)

    def delete_project(self, project_id: str):
        """Deletes a project."""
        if project_id in self.projects:
            del self.projects[project_id]