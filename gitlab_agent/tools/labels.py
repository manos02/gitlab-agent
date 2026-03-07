"""Label management tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class ListLabelsTool(JsonTool):
    tool_name = "list_labels"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        labels = gitlab.list_labels()
        if not labels:
            return "No labels found in this project."
        lines = [f"Found {len(labels)} label(s):\n"]
        for label in labels:
            lines.append(f"  - {label['name']} ({label['color']}): {label.get('description', '')}")
        return "\n".join(lines)


class CreateLabelTool(JsonTool):
    tool_name = "create_label"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        label = gitlab.create_label(
            name=kwargs["name"],
            color=kwargs.get("color", "#428BCA"),
            description=kwargs.get("description", ""),
        )
        return f"Label '{label['name']}' created with color {label['color']}."
