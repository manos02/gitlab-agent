"""Thin async wrapper around the GitLab REST API."""

from __future__ import annotations

from typing import Any

import httpx

from gitlab_agent.config import Config


class GitLabClient:
    """Handles authentication, requests, and pagination for the GitLab API."""

    def __init__(self, config: Config) -> None:
        self._base_url = f"{config.gitlab_url}/api/v4"
        self._project_id = config.gitlab_project_id
        self._headers = {"PRIVATE-TOKEN": config.gitlab_token}
        self._client = httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=30.0,
        )

    # -- helpers ---------------------------------------------------------------

    def _project_url(self, path: str) -> str:
        """Build a project-scoped API path."""
        return f"/projects/{self._project_id}{path}"

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
        return self._paginate(self._project_url("/issues"), params=params)

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
        return self._paginate(self._project_url("/merge_requests"), params=params)

    def get_merge_request(self, mr_iid: int) -> dict:
        return self._request("GET", self._project_url(f"/merge_requests/{mr_iid}"))

    def get_merge_request_pipelines(self, mr_iid: int) -> list[dict]:
        return self._paginate(self._project_url(f"/merge_requests/{mr_iid}/pipelines"))

    def get_merge_request_approvals(self, mr_iid: int) -> dict:
        return self._request("GET", self._project_url(f"/merge_requests/{mr_iid}/approvals"))

    # -- Boards ----------------------------------------------------------------

    def list_boards(self) -> list[dict]:
        return self._paginate(self._project_url("/boards"))

    def list_board_lists(self, board_id: int) -> list[dict]:
        return self._paginate(self._project_url(f"/boards/{board_id}/lists"))

    # -- Search ----------------------------------------------------------------

    def search_project(self, scope: str, search: str) -> list[dict]:
        """Search within the project. Scope: issues, merge_requests, milestones, etc."""
        return self._paginate(
            self._project_url("/search"),
            params={"scope": scope, "search": search},
        )

    # -- Milestones ------------------------------------------------------------

    def list_milestones(self, *, state: str = "active") -> list[dict]:
        return self._paginate(self._project_url("/milestones"), params={"state": state})

    # -- Cleanup ---------------------------------------------------------------

    def close(self) -> None:
        self._client.close()
