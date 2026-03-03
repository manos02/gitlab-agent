"""Core agent loop – orchestrates the LLM ↔ tool-calling conversation."""

from __future__ import annotations

import json
import re
from typing import Any, Callable

from gitlab_agent.config import Config
from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.llm.base import BaseLLMProvider
from gitlab_agent.llm.factory import create_llm_provider
from gitlab_agent.project_aliases import fetch_project_aliases
from gitlab_agent.tools.base import ToolRegistry
from gitlab_agent.tools.registry import create_default_registry


SYSTEM_PROMPT = """\
You are GitLab Agent, an AI assistant that helps users manage their GitLab projects \
through natural language.

You have access to tools that let you interact with the GitLab API. Use them to \
fulfill the user's requests. When the user asks you to do something, call the \
appropriate tool(s). You may need to chain multiple tool calls to complete a request \
(e.g., list boards first to find a board ID, then list its columns).

Guidelines:
- Be concise and helpful.
- When creating issues, ask for missing information only if truly ambiguous.
- When searching, try multiple approaches if the first doesn't find results.
- Always confirm what you did with a clear summary.
- If a tool call fails, explain the error and suggest a fix.
- Format IIDs as #N for issues and !N for merge requests.
"""

MAX_TOOL_ROUNDS = 10  # Safety limit on tool-calling rounds per user message


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
        self.project_aliases = self._initialize_project_aliases()

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    def chat(self, user_message: str) -> str:
        """Process a user message and return the agent's text response.

        This may involve multiple LLM ↔ tool rounds before producing a final answer.
        """
        self._resolve_project_alias_from_message(user_message)
        self.messages.append({"role": "user", "content": user_message})

        tool_schemas = self.registry.all_schemas()

        for _ in range(MAX_TOOL_ROUNDS):
            try:
                response = self.llm.chat(self.messages, tools=tool_schemas)
            except Exception as e:
                # Remove the user message so conversation stays clean
                self.messages.pop()
                raise RuntimeError(f"LLM request failed: {e}") from e

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

    def reset(self) -> None:
        """Clear conversation history (keep system prompt)."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    def close(self) -> None:
        """Clean up resources."""
        self.gitlab.close()

    def _resolve_project_alias_from_message(self, user_message: str) -> None:
        """Set active project when user mentions a known project alias in natural language."""
        if not self.project_aliases:
            return

        text = user_message.lower()
        matched_name = ""
        matched_project = ""

        for alias in sorted(self.project_aliases.keys(), key=len, reverse=True):
            if re.fullmatch(r"[\w\s]+", alias):
                pattern = rf"\b{re.escape(alias)}\b"
                matched = bool(re.search(pattern, text))
            else:
                matched = alias in text

            if matched:
                matched_name = alias
                matched_project = self.project_aliases[alias]
                break

        if not matched_name:
            return

        try:
            self.gitlab.set_project(matched_project)
            if self.on_tool_call:
                self.on_tool_call("set_active_project", {"project_alias": matched_name, "project": matched_project})
        except ValueError:
            return

    def _initialize_project_aliases(self) -> dict[str, str]:
        """Fetch aliases from GitLab /projects at startup."""
        try:
            return fetch_project_aliases(self.gitlab)
        except Exception:
            return {}
