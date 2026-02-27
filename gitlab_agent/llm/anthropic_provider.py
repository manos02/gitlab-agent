"""Anthropic LLM provider (Claude, etc.)."""

from __future__ import annotations

import json
import uuid
from typing import Any

import anthropic

from gitlab_agent.config import Config
from gitlab_agent.llm.base import BaseLLMProvider, LLMResponse, ToolCall


def _openai_tools_to_anthropic(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI function-calling tool schemas to Anthropic tool format."""
    converted = []
    for tool in tools:
        func = tool["function"]
        converted.append(
            {
                "name": func["name"],
                "description": func.get("description", ""),
                "input_schema": func.get("parameters", {"type": "object", "properties": {}}),
            }
        )
    return converted


def _openai_messages_to_anthropic(
    messages: list[dict[str, Any]],
) -> tuple[str, list[dict[str, Any]]]:
    """Split system message and convert the rest to Anthropic format.

    Returns (system_prompt, anthropic_messages).
    """
    system = ""
    anthropic_msgs: list[dict[str, Any]] = []

    for msg in messages:
        role = msg["role"]
        if role == "system":
            system = msg["content"]
        elif role == "assistant":
            # May contain tool_calls
            if msg.get("tool_calls"):
                content_blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["function"]["name"],
                            "input": args,
                        }
                    )
                anthropic_msgs.append({"role": "assistant", "content": content_blocks})
            else:
                anthropic_msgs.append({"role": "assistant", "content": msg["content"]})
        elif role == "tool":
            anthropic_msgs.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg["tool_call_id"],
                            "content": msg["content"],
                        }
                    ],
                }
            )
        else:
            # user
            anthropic_msgs.append({"role": "user", "content": msg["content"]})

    return system, anthropic_msgs


class AnthropicProvider(BaseLLMProvider):
    def __init__(self, config: Config) -> None:
        self._model = config.llm_model
        self._client = anthropic.Anthropic(api_key=config.anthropic_api_key)

    @property
    def model_name(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        system_prompt, anthropic_msgs = _openai_messages_to_anthropic(messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": anthropic_msgs,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = _openai_tools_to_anthropic(tools)

        response = self._client.messages.create(**kwargs)

        # Parse response blocks
        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=block.input,
                    )
                )

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls if tool_calls else None,
            raw=response,
        )
