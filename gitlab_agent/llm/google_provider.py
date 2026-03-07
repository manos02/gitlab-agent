"""Google Gemini LLM provider."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from google import genai
from google.genai import types as genai_types
from google.genai.errors import ClientError

from gitlab_agent.config import Config
from gitlab_agent.llm.base import BaseLLMProvider, LLMResponse, ToolCall

MAX_RETRIES = 3
RETRY_BASE_DELAY = 30 

def _openai_tools_to_gemini(tools: list[dict[str, Any]]) -> list[genai_types.Tool]:
    """Convert OpenAI function-calling tool schemas to Gemini format."""
    declarations = []
    for tool in tools:
        func = tool["function"]
        params = func.get("parameters", {})
        declarations.append(
            genai_types.FunctionDeclaration(
                name=func["name"],
                description=func.get("description", ""),
                parameters=params,
            )
        )
    return [genai_types.Tool(function_declarations=declarations)]


def _openai_messages_to_gemini(
    messages: list[dict[str, Any]],
) -> tuple[str, list[genai_types.Content]]:
    """Convert OpenAI message list to Gemini contents.

    Returns (system_instruction, contents).
    """
    system = ""
    contents: list[genai_types.Content] = []

    for msg in messages:
        role = msg["role"]
        if role == "system":
            system = msg["content"]
        elif role == "user":
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[genai_types.Part.from_text(text=msg["content"])],
                )
            )
        elif role == "assistant":
            parts: list[genai_types.Part] = []
            if msg.get("content"):
                parts.append(genai_types.Part.from_text(text=msg["content"]))
            if msg.get("tool_calls"):
                for tc in msg["tool_calls"]:
                    args = tc["function"]["arguments"]
                    if isinstance(args, str):
                        args = json.loads(args)
                    parts.append(
                        genai_types.Part.from_function_call(
                            name=tc["function"]["name"],
                            args=args,
                        )
                    )
            contents.append(genai_types.Content(role="model", parts=parts))
        elif role == "tool":
            contents.append(
                genai_types.Content(
                    role="user",
                    parts=[
                        genai_types.Part.from_function_response(
                            name=msg.get("name", "tool"),
                            response={"result": msg["content"]},
                        )
                    ],
                )
            )

    return system, contents


class GoogleProvider(BaseLLMProvider):
    def __init__(self, config: Config) -> None:
        self._model = config.llm_model
        self._client = genai.Client(api_key=config.llm_key)

    @property
    def model_name(self) -> str:
        return self._model

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        system_instruction, contents = _openai_messages_to_gemini(messages)

        config = genai_types.GenerateContentConfig(
            system_instruction=system_instruction if system_instruction else None,
        )
        if tools:
            config.tools = _openai_tools_to_gemini(tools)

        # Retry on rate-limit (429) errors
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES):
            try:
                response = self._client.models.generate_content(
                    model=self._model,
                    contents=contents,
                    config=config,
                )
                break
            except ClientError as e:
                if e.code == 429:
                    last_error = e
                    wait = RETRY_BASE_DELAY * (attempt + 1)
                    import sys
                    print(
                        f"\n⏳ Rate limited by Gemini API. Retrying in {wait}s "
                        f"(attempt {attempt + 1}/{MAX_RETRIES})...",
                        file=sys.stderr,
                    )
                    time.sleep(wait)
                else:
                    raise
        else:
            raise RuntimeError(
                f"Gemini API rate limit exceeded after {MAX_RETRIES} retries. "
                "Wait a minute and try again, or switch to a paid tier."
            ) from last_error

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []

        if response.candidates and response.candidates[0].content:
            for part in response.candidates[0].content.parts:
                if part.text:
                    text_parts.append(part.text)
                elif part.function_call:
                    tool_calls.append(
                        ToolCall(
                            id=uuid.uuid4().hex[:8],
                            name=part.function_call.name,
                            arguments=dict(part.function_call.args) if part.function_call.args else {},
                        )
                    )

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls if tool_calls else None,
            raw=response,
        )
