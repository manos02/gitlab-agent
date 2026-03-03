"""Thin async wrapper around the GitLab REST API."""

from __future__ import annotations

from typing import Any
from urllib.parse import quote

import httpx

from gitlab_agent.config import Config


class GitLabClient:
    """Handles authentication, requests, and pagination for the GitLab API."""

    def __init__(self, config: Config) -> None:
        self._base_url = f"{config.gitlab_url}/api/v4"
        self._project_id = ""
        self._group_id = config.gitlab_group_id
        self._headers = {"PRIVATE-TOKEN": config.gitlab_token}
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    # -- helpers ---------------------------------------------------------------

    def current_project(self) -> str | None:
        """Return the currently selected project (ID or path), if any."""
        return self._project_id or None

    def current_group(self) -> str | None:
        """Return the currently selected group (ID or path), if any."""
        return self._group_id or None

    def set_project(self, project_id_or_path: str) -> None:
        """Set active project for all subsequent project-scoped calls.

        Accepts numeric project ID (e.g. "123") or full path (e.g. "group/subgroup/repo").
        """
        value = project_id_or_path.strip()
        if not value:
            raise ValueError("Project cannot be empty")
        self._project_id = value

    def set_group(self, group_id_or_path: str) -> None:
        """Set active group for group-scoped calls.

        Accepts numeric group ID (e.g. "42") or full path (e.g. "mygroup/platform").
        """
        value = group_id_or_path.strip()
        if not value:
            raise ValueError("Group cannot be empty")
        self._group_id = value

    def _group_ref(self) -> str:
        """Return encoded group reference for URLs."""
        if not self._group_id:
            raise ValueError(
                "No GitLab group selected. Set GITLAB_GROUP_ID in .env or use /group <id-or-path> in the CLI."
            )

        group = self._group_id.strip()
        if group.isdigit():
            return group
        return quote(group, safe="")

    def _project_ref(self) -> str:
        """Return encoded project reference for URLs."""
        if not self._project_id:
            raise ValueError(
                "No GitLab project selected. Use /project <id-or-path> in the CLI or mention a mapped project name in chat."
            )

        project = self._project_id.strip()
        if project.isdigit():
            return project
        return quote(project, safe="")

    def _project_url(self, path: str) -> str:
        """Build a project-scoped API path."""
        return f"/projects/{self._project_ref()}{path}"

    def _group_url(self, path: str) -> str:
        """Build a group-scoped API path."""
        return f"/groups/{self._group_ref()}{path}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Make an API request and return parsed JSON."""
        resp = self._client.request(method, path, params=params, json=json)
        resp.raise_for_status()
        if resp.status_code == 204:
            return None
        return resp.json()

    def _paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 5,
    ) -> list[Any]:
        """Fetch multiple pages and merge results."""
        params = dict(params or {})
        params.setdefault("per_page", 20)
        results: list[Any] = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
            if not data:
                break
            results.extend(data)
        return results

    # -- Generic public API ----------------------------------------------------

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> Any:
        """Public generic request method for rebuilding endpoint wrappers from scratch."""
        return self._request(method, path, params=params, json=json)

    def paginate(
        self,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        max_pages: int = 5,
    ) -> list[Any]:
        """Public generic pagination method for rebuilding endpoint wrappers from scratch."""
        return self._paginate(path, params=params, max_pages=max_pages)

    # -- Cleanup ---------------------------------------------------------------

    def close(self) -> None:
        self._client.close()
