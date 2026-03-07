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

    def clear_project(self) -> None:
        """Clear active project so calls can fall back to group scope."""
        self._project_id = ""

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
        max_pages: int = 10,
    ):
        """Fetch multiple pages and merge results."""
        params = dict(params or {})
        params.setdefault("per_page", 100) # max page result for gitlab api
        results = []
        page = 1
        for page in range(1, max_pages + 1):
            params["page"] = page
            resp = self._client.get(path, params=params)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data)
            if not resp.headers['x-next-page']: # if we fetched all the results then x-next-page will be empty string 
                break
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

    # -- Projects --------------------------------------------------------------

    def list_projects(
        self,
        *,
        search: str = "",
        membership: bool = True,
        archived: bool = False,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "simple": True,
            "membership": membership,
            "archived": archived,
        }
        if search:
            params["search"] = search
        return self._paginate("/projects", params=params)

    # -- Issues ----------------------------------------------------------------

    def create_issue(
        self,
        title: str,
        *,
        description: str = "",
        labels: str = "",
        assignee_ids: list[int] | None = None,
        milestone_id: int | None = None,
    ) -> dict:
        body: dict[str, Any] = {"title": title}
        if description:
            body["description"] = description
        if labels:
            body["labels"] = labels
        if assignee_ids:
            body["assignee_ids"] = assignee_ids
        if milestone_id:
            body["milestone_id"] = milestone_id
        return self._request("POST", self._project_url("/issues"), json=body)

    def get_issue(self, issue_iid: int) -> dict:
        return self._request("GET", self._project_url(f"/issues/{issue_iid}"))

    def list_issues(
        self,
        *,
        state: str = "opened",
        labels: str = "",
        search: str = "",
        milestone: str = "",
    ) -> list[dict]:
        params: dict[str, Any] = {"state": state}
        if labels:
            params["labels"] = labels
        if search:
            params["search"] = search
        if milestone:
            params["milestone"] = milestone
        if self._project_id:
            return self._paginate(self._project_url("/issues"), params=params)
        if self._group_id:
            return self._paginate(self._group_url("/issues"), params=params)
        raise ValueError(
            "No scope selected for listing issues. Use /project <id-or-path> or /group <id-or-path>."
        )

    def update_issue(self, issue_iid: int, **fields: Any) -> dict:
        return self._request("PUT", self._project_url(f"/issues/{issue_iid}"), json=fields)

    def close_issue(self, issue_iid: int) -> dict:
        return self.update_issue(issue_iid, state_event="close")

    # -- Labels ----------------------------------------------------------------

    def list_labels(self) -> list[dict]:
        return self._paginate(self._project_url("/labels"))

    def create_label(self, name: str, color: str = "#428BCA", description: str = "") -> dict:
        body: dict[str, Any] = {"name": name, "color": color}
        if description:
            body["description"] = description
        return self._request("POST", self._project_url("/labels"), json=body)

    # -- Merge Requests --------------------------------------------------------

    def list_merge_requests(
        self,
        *,
        state: str = "opened",
        search: str = "",
    ) -> list[dict]:
        params: dict[str, Any] = {"state": state}
        if search:
            params["search"] = search
        if self._project_id:
            return self._paginate(self._project_url("/merge_requests"), params=params)
        if self._group_id:
            return self._paginate(self._group_url("/merge_requests"), params=params)
        raise ValueError(
            "No scope selected for listing merge requests. Use /project <id-or-path> or /group <id-or-path>."
        )

    def get_merge_request(self, mr_iid: int) -> dict:
        return self._request("GET", self._project_url(f"/merge_requests/{mr_iid}"))

    def get_merge_request_pipelines(self, mr_iid: int) -> list[dict]:
        return self._paginate(self._project_url(f"/merge_requests/{mr_iid}/pipelines"))

    def get_merge_request_approvals(self, mr_iid: int) -> dict:
        return self._request("GET", self._project_url(f"/merge_requests/{mr_iid}/approvals"))

    # -- Boards ----------------------------------------------------------------

    def list_boards(self) -> list[dict]:
        if self._project_id:
            return self._paginate(self._project_url("/boards"))
        if self._group_id:
            return self._paginate(self._group_url("/boards"))
        raise ValueError(
            "No scope selected for boards. Use /project <id-or-path> or /group <id-or-path>."
        )

    def list_board_lists(self, board_id: int) -> list[dict]:
        if self._project_id:
            return self._paginate(self._project_url(f"/boards/{board_id}/lists"))
        if self._group_id:
            return self._paginate(self._group_url(f"/boards/{board_id}/lists"))
        raise ValueError(
            "No scope selected for board lists. Use /project <id-or-path> or /group <id-or-path>."
        )

    # -- Search ----------------------------------------------------------------

    def search_project(self, scope: str, search: str) -> list[dict]:
        if self._project_id:
            return self._paginate(
                self._project_url("/search"),
                params={"scope": scope, "search": search},
            )
        if self._group_id:
            return self._paginate(
                self._group_url("/search"),
                params={"scope": scope, "search": search},
            )
        raise ValueError(
            "No scope selected for search. Use /project <id-or-path> or /group <id-or-path>."
        )

    # -- Milestones ------------------------------------------------------------

    def list_milestones(self, *, state: str = "active") -> list[dict]:
        if self._project_id:
            return self._paginate(self._project_url("/milestones"), params={"state": state})
        if self._group_id:
            return self._paginate(self._group_url("/milestones"), params={"state": state})
        raise ValueError(
            "No scope selected for milestones. Use /project <id-or-path> or /group <id-or-path>."
        )

    # -- Groups ----------------------------------------------------------------

    def get_group(self) -> dict:
        return self._request("GET", self._group_url(""))

    def list_group_projects(
        self,
        *,
        search: str = "",
        include_subgroups: bool = True,
        with_shared: bool = False,
    ) -> list[dict]:
        params: dict[str, Any] = {
            "include_subgroups": include_subgroups,
            "with_shared": with_shared,
            "simple": True,
        }
        if search:
            params["search"] = search
        return self._paginate(self._group_url("/projects"), params=params)

    # -- Cleanup ---------------------------------------------------------------

    def close(self) -> None:
        self._client.close()
