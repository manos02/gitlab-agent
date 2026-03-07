"""Core agent loop – orchestrates the LLM ↔ tool-calling conversation."""

from __future__ import annotations

import json
from typing import Any, Callable

from gitlab_agent.config import Config
from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.llm.base import BaseLLMProvider
from gitlab_agent.llm.factory import create_llm_provider
from gitlab_agent.resources import get_agent_settings
from gitlab_agent.tools.base import ToolRegistry
from gitlab_agent.tools.registry import create_default_registry
from gitlab_agent.tools.utils import (
    _aliases_from_projects,
    _best_project_alias_match,
)


AGENT_SETTINGS = get_agent_settings()
SYSTEM_PROMPT = AGENT_SETTINGS["system_prompt"]
MAX_TOOL_ROUNDS = AGENT_SETTINGS["max_tool_rounds"]


class Agent:
    """The core agent that connects user input → LLM → tools → GitLab."""

    def __init__(
        self,
        config: Config,
        *,
        llm: BaseLLMProvider | None = None,
        gitlab: GitLabClient | None = None,
        registry: ToolRegistry | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.config = config
        self.llm = llm or create_llm_provider(config)
        self.gitlab = gitlab or GitLabClient(config)
        self.registry = registry or create_default_registry()
        self.on_tool_call = on_tool_call  # callback for UI to display tool activity
        self.project_aliases = None
        self._project_set_by_alias = False
        self.tool_schemas = self.registry.all_schemas()

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def chat(self, user_message: str) -> str:
        """Process a user message and return the agent's text response.

        This may involve multiple LLM ↔ tool rounds before producing a final answer.
        """
        project_matched = self._resolve_project_alias_from_message(user_message)
        self.messages.append(
            {"role": "system", "content": self._scope_hint_message(project_matched)}
        )
        self.messages.append({"role": "user", "content": user_message})

        try:
            for _ in range(MAX_TOOL_ROUNDS):
                response = self.llm.chat(self.messages, tools=self.tool_schemas)
                # If no tool calls, we have a final text response
                if not response.tool_calls:
                    assistant_text = response.content or ""
                    self.messages.append({"role": "assistant", "content": assistant_text})
                    return assistant_text

                # Build assistant message with tool calls (OpenAI format for history)
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": response.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.name,
                                "arguments": json.dumps(tc.arguments),
                            },
                        }
                        for tc in response.tool_calls
                    ],
                }
                self.messages.append(assistant_msg)

                # Execute each tool call
                for tc in response.tool_calls:
                    if self.on_tool_call:
                        self.on_tool_call(tc.name, tc.arguments)

                    tool = self.registry.get(tc.name)
                    if tool is None:
                        result = f"Error: Unknown tool '{tc.name}'"
                    else:
                        try:
                            result = tool.run(self.gitlab, **tc.arguments)
                        except Exception as e:
                            result = f"Error executing {tc.name}: {e}"

                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result,
                        }
                    )

            # Exceeded max rounds
            return "I've reached the maximum number of tool-calling rounds. Please try a simpler request or break it into steps."
        except Exception as e:
            # Remove transient request-scoping messages so conversation stays clean
            self.messages.pop()
            self.messages.pop()
            raise RuntimeError(f"LLM request failed: {e}") from e
        finally:
            if self._project_set_by_alias:
                self.gitlab.clear_project()
                self._project_set_by_alias = False

    def reset(self) -> None:
        """Clear conversation history (keep system prompt)."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def close(self) -> None:
        """Clean up resources."""
        self.gitlab.close()

    def _scope_hint_message(self, project_matched: bool) -> str:
        """Describe the scope the model should assume for the current request."""
        current_project = self.gitlab.current_project()
        if project_matched and current_project:
            return (
                f"Scope hint: the user message matched project '{current_project}'. "
                "Prefer project-scoped calls for this request."
            )

        current_group = self.gitlab.current_group()
        if current_group:
            return (
                f"Scope hint: no project alias matched in this user message. The active default "
                f"scope is GitLab group '{current_group}'. Treat this as a broader group-level "
                "request, prefer group-scoped listing/search calls, and only ask for a specific "
                "project if the task truly requires project scope."
            )

        return (
            "Scope hint: no project alias matched and no default group is set. Ask for a project "
            "or group only when the requested action needs one."
        )

    def _resolve_project_alias_from_message(self, user_message: str) -> bool:
        """Set active project when user mentions a known project alias in natural language."""
        if not self.project_aliases:
            if self._project_set_by_alias:
                self.gitlab.clear_project()
                self._project_set_by_alias = False
            return False

        project_id, project_name = _best_project_alias_match(user_message, self.project_aliases)
        if not project_id:
            if self._project_set_by_alias:
                self.gitlab.clear_project()
                self._project_set_by_alias = False
            return False

        if self.on_tool_call:
            self.on_tool_call(
                "set_active_project",
                {"project_name": project_name, "project_id": project_id},
            )

        self.gitlab.set_project(project_id)
        self._project_set_by_alias = True
        return True

    def initialize_project_aliases(self) -> dict[str, dict[str, str | set[str]]]:
        """Fetch aliases from GitLab /projects at startup."""
        return _aliases_from_projects(self.gitlab)
