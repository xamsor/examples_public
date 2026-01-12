import os
import requests
from dotenv import load_dotenv

load_dotenv()

class ClickUpClient:
    BASE_URL = "https://api.clickup.com/api/v2"

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("CLICKUP_API_KEY")
        if not self.api_key:
            raise ValueError("API key is required. Set CLICKUP_API_KEY in .env or pass it directly.")
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json"
        }

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        url = f"{self.BASE_URL}/{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()

    # User & Workspace
    def get_user(self) -> dict:
        """Get authenticated user info."""
        return self._request("GET", "user")

    def get_teams(self) -> dict:
        """Get all workspaces (teams) the user has access to."""
        return self._request("GET", "team")

    # Spaces
    def get_spaces(self, team_id: str) -> dict:
        """Get all spaces in a workspace."""
        return self._request("GET", f"team/{team_id}/space")

    # Folders
    def get_folders(self, space_id: str) -> dict:
        """Get all folders in a space."""
        return self._request("GET", f"space/{space_id}/folder")

    # Lists
    def get_lists(self, folder_id: str) -> dict:
        """Get all lists in a folder."""
        return self._request("GET", f"folder/{folder_id}/list")

    def get_folderless_lists(self, space_id: str) -> dict:
        """Get lists not in any folder."""
        return self._request("GET", f"space/{space_id}/list")

    # Tasks
    def get_tasks(self, list_id: str, **params) -> dict:
        """Get tasks in a list."""
        return self._request("GET", f"list/{list_id}/task", params=params)

    def get_task(self, task_id: str) -> dict:
        """Get a specific task."""
        return self._request("GET", f"task/{task_id}")

    def create_task(self, list_id: str, name: str, **kwargs) -> dict:
        """Create a new task in a list."""
        data = {"name": name, **kwargs}
        return self._request("POST", f"list/{list_id}/task", json=data)

    def update_task(self, task_id: str, **kwargs) -> dict:
        """Update an existing task."""
        return self._request("PUT", f"task/{task_id}", json=kwargs)

    def delete_task(self, task_id: str) -> dict:
        """Delete a task."""
        return self._request("DELETE", f"task/{task_id}")

    # Docs (v3 API)
    def search_docs(self, workspace_id: str, **params) -> dict:
        """Search docs in a workspace."""
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs"
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def get_doc(self, workspace_id: str, doc_id: str) -> dict:
        """Get a specific doc."""
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_doc(self, workspace_id: str, name: str, parent: dict = None, **kwargs) -> dict:
        """
        Create a new doc in a workspace.

        Args:
            workspace_id: The workspace ID
            name: Name of the doc
            parent: Dict with 'id' and 'type' (e.g., {"id": "folder_id", "type": 4} for folder)
                   Types: 4=folder, 5=list, 6=task, 7=space, 12=everything_level
        """
        data = {"name": name, **kwargs}
        if parent:
            data["parent"] = parent
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs"
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_doc_pages(self, workspace_id: str, doc_id: str) -> dict:
        """Get all pages in a doc."""
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages"
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        return response.json()

    def create_doc_page(self, workspace_id: str, doc_id: str, name: str, content: str = None, **kwargs) -> dict:
        """Create a new page in a doc."""
        data = {"name": name, **kwargs}
        if content:
            data["content"] = content
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages"
        response = requests.post(url, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

    def get_page_content(self, workspace_id: str, doc_id: str, page_id: str, content_format: str = "markdown") -> dict:
        """
        Get content of a specific page.

        Args:
            content_format: 'markdown' or 'text'
        """
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}"
        params = {"content_format": content_format}
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        return response.json()

    def edit_page(self, workspace_id: str, doc_id: str, page_id: str, **kwargs) -> dict:
        """
        Edit a page in a doc.

        Args:
            name: New name for the page
            content: New content (markdown)
            content_edit_mode: 'replace', 'append', or 'prepend'
        """
        url = f"https://api.clickup.com/api/v3/workspaces/{workspace_id}/docs/{doc_id}/pages/{page_id}"
        response = requests.put(url, headers=self.headers, json=kwargs)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    client = ClickUpClient()

    # Test: Get user info
    print("=== User Info ===")
    user = client.get_user()
    print(f"Username: {user['user']['username']}")
    print(f"Email: {user['user']['email']}")

    # Test: Get workspaces
    print("\n=== Workspaces ===")
    teams = client.get_teams()
    for team in teams["teams"]:
        print(f"- {team['name']} (ID: {team['id']})")

        # Get spaces in this workspace
        print("\n=== Spaces ===")
        spaces = client.get_spaces(team["id"])
        for space in spaces["spaces"]:
            print(f"  - {space['name']} (ID: {space['id']})")

    # Test: Search docs
    print("\n=== Docs ===")
    workspace_id = teams["teams"][0]["id"]
    try:
        docs = client.search_docs(workspace_id)
        for doc in docs.get("docs", []):
            print(f"  - {doc.get('name', 'Untitled')} (ID: {doc.get('id')})")
    except Exception as e:
        print(f"  Could not fetch docs: {e}")
