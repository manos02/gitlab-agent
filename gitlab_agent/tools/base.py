"""Base tool class and registry.

Every tool self-describes its name, description, and JSON-schema parameters so that
any LLM provider can use it via function / tool calling.
"""

from __future__ import annotations

import copy
import json
from abc import ABC, abstractmethod
from typing import Any, ClassVar

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.resources import get_tool_schemas


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
        self._schema_cache: list[dict[str, Any]] | None = None

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool
        self._schema_cache = None

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def all_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-format tool schemas for all registered tools."""
        if self._schema_cache is None:
            self._schema_cache = [t.to_openai_schema() for t in self._tools.values()]
        return self._schema_cache

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)


class JsonTool(Tool):
    """Tool whose model-facing metadata is loaded from packaged JSON."""

    tool_name: ClassVar[str]

    @property
    def name(self) -> str:
        return self.tool_name

    @property
    def description(self) -> str:
        return self._metadata()["description"]

    @property
    def parameters(self) -> dict[str, Any]:
        return copy.deepcopy(self._metadata()["parameters"])

    def _metadata(self) -> dict[str, Any]:
        metadata = get_tool_schemas().get(self.tool_name)
        if metadata is None:
            raise KeyError(f"Missing tool schema metadata for '{self.tool_name}'")
        return metadata
