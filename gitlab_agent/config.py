"""Configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import field
from pathlib import Path
from pydantic import BaseModel, field_validator
from dotenv import load_dotenv


# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.5-flash",
    "ollama": "qwen2.5",
}

DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434/v1"


class Config(BaseModel):
    """Immutable application configuration."""

    # LLM
    llm_provider: str
    llm_model: str
    llm_key: str
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL

    # GitLab
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: str = field(default="", repr=False)
    gitlab_group_id: str = ""

    @field_validator("llm_provider")
    @classmethod
    def api_key_required(cls, value):
        if value not in DEFAULT_MODELS:
            raise ValueError(f"LLM_PROVIDER must be one of {list(DEFAULT_MODELS.keys())}, "
                f"got '{value}'")
        return value

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> Config:
        load_dotenv(env_path) # Load the env file with optional path
        return cls(
            llm_provider=os.getenv("LLM_PROVIDER"),
            llm_model=os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(cls.llm_provider),
            llm_key=os.getenv("API_KEY"),
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            gitlab_url=os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/"),
            gitlab_token=os.getenv("GITLAB_TOKEN", ""),
            gitlab_group_id=os.getenv("GITLAB_GROUP_ID", ""),
        )
