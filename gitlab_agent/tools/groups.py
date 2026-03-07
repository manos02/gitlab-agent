"""Group-scoped tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import Tool


class GetGroupInfoTool(Tool):
    @property
    def name(self) -> str:
        return "get_group_info"

    @property
    def description(self) -> str:
        return "Get details for the active GitLab group."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        _ = kwargs
        group = gitlab.get_group()
        visibility = group.get("visibility", "unknown")
        full_path = group.get("full_path", group.get("path", "?"))
        web_url = group.get("web_url", "")
        return (
            f"Group: {group.get('name', '?')}\n"
            f"Path: {full_path}\n"
            f"Visibility: {visibility}\n"
            f"Web URL: {web_url}\n"
            f"Description: {group.get('description') or '(none)'}"
        )


class ListGroupProjectsTool(Tool):
    @property
    def name(self) -> str:
        return "list_group_projects"

    @property
    def description(self) -> str:
        return "List projects in the active group, with optional search filter."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search": {
                    "type": "string",
                    "description": "Optional search text for group projects",
                    "default": "",
                },
                "include_subgroups": {
                    "type": "boolean",
                    "description": "Include subgroup projects",
                    "default": True,
                },
            },
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        projects = gitlab.list_group_projects(
            search=kwargs.get("search", ""),
            include_subgroups=kwargs.get("include_subgroups", True),
        )
        if not projects:
            return "No group projects found."

        lines = [f"Found {len(projects)} group project(s):\n"]
        for project in projects[:30]:
            lines.append(
                f"  {project.get('name_with_namespace', project.get('name', '?'))}"
                f"  id: {project.get('id', '?')}"
                f"  path: {project.get('path_with_namespace', '?')}"
            )
        return "\n".join(lines)
