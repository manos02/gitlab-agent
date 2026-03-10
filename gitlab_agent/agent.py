"""CLI chat agent backed by LLM function calling and a FastMCP client session."""

from __future__ import annotations

import json
from typing import Any, Callable

from fastmcp import Client, FastMCP

from gitlab_agent.config import Config
from gitlab_agent.llm.base import BaseLLMProvider
from gitlab_agent.llm.factory import create_llm_provider
from gitlab_agent.server import mcp


SYSTEM_PROMPT = """You are GitLab Agent, an AI assistant that helps users manage their GitLab projects through natural language.

You have access to tools that let you interact with the GitLab API. Use them to fulfill the user's requests. You may need to chain multiple tool calls to complete a request.

Guidelines:
- Be concise and helpful.
- If the user mentions a project naturally, prefer set_active_project_from_query before project-scoped calls.
- When creating issues, ask for missing information only if truly ambiguous.
- When searching, try multiple approaches if the first doesn't find results.
- Always confirm what you did with a clear summary.
- If a tool call fails, explain the error and suggest a fix.
- Format IIDs as #N for issues and !N for merge requests.
"""
MAX_TOOL_ROUNDS = 10
SESSION_CONTEXT_PREFIX = "Session context for project routing:"


def _fastmcp_tools_to_openai_schema(tools: list[Any]) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in tools
    ]


def _tool_result_to_text(result: Any) -> str:
    if getattr(result, "data", None) is not None:
        data = result.data
        if isinstance(data, str):
            return data
        return json.dumps(data, ensure_ascii=True)

    content = getattr(result, "content", None) or []
    text_parts = [block.text for block in content if getattr(block, "type", None) == "text"]
    if text_parts:
        return "\n".join(text_parts)
    return ""


class Agent:
    """Chat agent that uses provider function-calling against the FastMCP server."""

    def __init__(
        self,
        config: Config,
        *,
        llm: BaseLLMProvider | None = None,
        mcp_server: FastMCP | None = None,
        on_tool_call: Callable[[str, dict], None] | None = None,
    ) -> None:
        self.config = config
        self.llm = llm or create_llm_provider(config)
        self.client = Client(mcp_server or mcp)
        self.on_tool_call = on_tool_call  # callback for UI to display tool activity
        self.tool_schemas: list[dict[str, Any]] = []
        self._opened = False
        self._session_context_index: int | None = None

        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

    async def _refresh_session_context(self, *, refresh_catalog: bool = False) -> None:
        scope = await self.get_active_scope()
        try:
            catalog_result = await self.client.call_tool(
                "get_project_catalog",
                {"refresh": refresh_catalog, "limit": 200},
            )
            catalog = _tool_result_to_text(catalog_result)
        except Exception as exc:
            catalog = (
                "Project catalog is currently unavailable because the GitLab project listing request failed. "
                f"Error: {exc}. If this keeps happening, set a narrower default group or increase GITLAB_TIMEOUT."
            )
        content = (
            f"{SESSION_CONTEXT_PREFIX}\n"
            f"{scope}\n\n"
            f"The project catalog below was fetched from GitLab for this session. "
            f"If the user mentions one of these projects, use its mapped id or path for project-scoped calls. "
            f"If the prompt does not refer to one of these projects, keep the request generic and prefer group scope.\n\n"
            f"{catalog}"
        )

        if self._session_context_index is None or self._session_context_index >= len(self.messages):
            self.messages.append({"role": "system", "content": content})
            self._session_context_index = len(self.messages) - 1
        else:
            self.messages[self._session_context_index] = {"role": "system", "content": content}

    async def open(self) -> None:
        if self._opened:
            return
        await self.client.__aenter__()
        self.tool_schemas = _fastmcp_tools_to_openai_schema(await self.client.list_tools())
        self._opened = True
        await self._refresh_session_context(refresh_catalog=True)

    async def chat(self, user_message: str) -> str:
        """Process a user message and return the agent's text response."""
        if not self._opened:
            await self.open()
        else:
            await self._refresh_session_context()

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

                    try:
                        call_result = await self.client.call_tool(tc.name, tc.arguments)
                        result = _tool_result_to_text(call_result)
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
            self.messages.pop()
            raise RuntimeError(f"LLM request failed: {e}") from e

    def reset(self) -> None:
        """Clear conversation history while keeping the MCP session state."""
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        self._session_context_index = None

    async def get_active_scope(self) -> str:
        result = await self.client.call_tool("get_active_scope")
        return _tool_result_to_text(result)

    async def get_project_catalog(self, *, refresh: bool = False, limit: int = 100) -> str:
        result = await self.client.call_tool(
            "get_project_catalog",
            {"refresh": refresh, "limit": limit},
        )
        return _tool_result_to_text(result)

    async def list_group_projects(
        self,
        *,
        search: str = "",
        include_subgroups: bool = True,
    ) -> str:
        result = await self.client.call_tool(
            "list_group_projects",
            {"search": search, "include_subgroups": include_subgroups},
        )
        return _tool_result_to_text(result)

    async def set_group(self, group_id_or_path: str) -> str:
        result = await self.client.call_tool(
            "set_active_group", {"group_id_or_path": group_id_or_path}
        )
        await self._refresh_session_context(refresh_catalog=True)
        return _tool_result_to_text(result)

    async def set_project(self, project_id_or_path: str) -> str:
        result = await self.client.call_tool(
            "set_active_project", {"project_id_or_path": project_id_or_path}
        )
        await self._refresh_session_context()
        return _tool_result_to_text(result)

    async def clear_project(self) -> str:
        result = await self.client.call_tool("clear_active_project")
        await self._refresh_session_context()
        return _tool_result_to_text(result)

    async def close(self) -> None:
        """Clean up resources."""
        if not self._opened:
            return
        await self.client.__aexit__(None, None, None)
        self._opened = False
