"""Base tool class and registry.

Every tool self-describes its name, description, and JSON-schema parameters so that
any LLM provider can use it via function / tool calling.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from gitlab_agent.gitlab_client import GitLabClient


class Tool(ABC):
    """Base class for all GitLab Agent tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name (snake_case, e.g. 'create_issue')."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """One-line description the LLM sees to decide when to call this tool."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema describing the tool's input parameters."""
        ...

    @abstractmethod
    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        """Execute the tool and return a human-readable result string.

        The result is sent back to the LLM as the tool response.
        """
        ...

    def to_openai_schema(self) -> dict[str, Any]:
        """Return the tool definition in OpenAI function-calling format.

        This is also the format we use internally; Anthropic/Google providers
        convert from this format automatically.
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Collects tools and provides lookup + schema export."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool schemas for all registered tools."""
        return [t.to_openai_schema() for t in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
