"""Group-scoped tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class GetGroupInfoTool(JsonTool):
    tool_name = "get_group_info"

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


class ListGroupProjectsTool(JsonTool):
    tool_name = "list_group_projects"

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
