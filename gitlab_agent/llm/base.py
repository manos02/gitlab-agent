"""Abstract base class that every LLM provider must implement."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """Represents the LLM's request to invoke a tool."""
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    """Unified response from any provider."""
    content: str | None = None           # text reply (may be None when tool calls present)
    tool_calls: list[ToolCall] | None = None  # requested tool invocations
    raw: Any = None                       # provider-specific raw response


class BaseLLMProvider(ABC):
    """Interface that every LLM provider must implement."""

    @abstractmethod
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        """Send a conversation to the model and return a unified response.

        Parameters
        ----------
        messages:
            OpenAI-style message list [{"role": ..., "content": ...}, ...].
        tools:
            List of tool schemas (OpenAI function-calling format).

        Returns
        -------
        LLMResponse with either content or tool_calls (or both).
        """
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier being used."""
        ...
