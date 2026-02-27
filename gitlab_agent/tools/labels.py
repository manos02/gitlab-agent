"""Label management tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import Tool


class ListLabelsTool(Tool):
    @property
    def name(self) -> str:
        return "list_labels"

    @property
    def description(self) -> str:
        return "List all labels available in the project."

    @property
    def parameters(self) -> dict[str, Any]:
        return {"type": "object", "properties": {}}

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        labels = gitlab.list_labels()
        if not labels:
            return "No labels found in this project."
        lines = [f"Found {len(labels)} label(s):\n"]
        for label in labels:
            lines.append(f"  - {label['name']} ({label['color']}): {label.get('description', '')}")
        return "\n".join(lines)


class CreateLabelTool(Tool):
    @property
    def name(self) -> str:
        return "create_label"

    @property
    def description(self) -> str:
        return "Create a new label in the project."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Label name",
                },
                "color": {
                    "type": "string",
                    "description": "Hex color code, e.g. '#FF0000'",
                    "default": "#428BCA",
                },
                "description": {
                    "type": "string",
                    "description": "Label description",
                    "default": "",
                },
            },
            "required": ["name"],
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        label = gitlab.create_label(
            name=kwargs["name"],
            color=kwargs.get("color", "#428BCA"),
            description=kwargs.get("description", ""),
        )
        return f"Label '{label['name']}' created with color {label['color']}."
