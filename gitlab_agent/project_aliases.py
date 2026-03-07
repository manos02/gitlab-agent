"""Load project-name aliases used for natural-language project selection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gitlab_agent.gitlab_client import GitLabClient


def _aliases_from_projects(projects: list[dict]) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for project in projects:
        project_id = project.get("id")
        if project_id is None:
            continue

        project_ref = str(project_id)
        project_name = project.get("name").strip().lower() 
        aliases[project_name] = project_ref

    return aliases


def fetch_project_aliases(gitlab: "GitLabClient") -> dict[str, str]:
    """Fetch projects and build in-memory aliases.

    Returns lowercase alias names mapped to project IDs.
    """
    projects = gitlab.list_projects()
    return _aliases_from_projects(projects)
