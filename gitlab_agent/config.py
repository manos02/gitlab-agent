"""Configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from pathlib import Path
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv
from gitlab_agent.resources import get_llm_defaults


LLM_DEFAULTS = get_llm_defaults()
DEFAULT_MODELS: dict[str, str] = LLM_DEFAULTS["default_models"]
DEFAULT_OLLAMA_BASE_URL = LLM_DEFAULTS["default_ollama_base_url"]


class Config(BaseModel):
    """Immutable application configuration."""

    # LLM
    llm_provider: str = "ollama"
    llm_model: str = ""
    llm_key: str = Field(default="", repr=False)
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL

    # GitLab
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: str = Field(default="", repr=False)
    gitlab_group_id: str = ""

    @field_validator("llm_provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        if value not in DEFAULT_MODELS:
            raise ValueError(
                f"LLM_PROVIDER must be one of {list(DEFAULT_MODELS.keys())}, got '{value}'"
            )
        return value

    @property
    def requires_api_key(self) -> bool:
        return self.llm_provider != "ollama"

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> Config:
        load_dotenv(env_path)
        provider = (os.getenv("LLM_PROVIDER") or "ollama").strip().lower()
        provider_key_env = {
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
            "google": "GOOGLE_API_KEY",
            "ollama": "API_KEY",
        }
        llm_key = os.getenv(provider_key_env.get(provider, "API_KEY"), "") or os.getenv(
            "API_KEY", ""
        )
        return cls(
            llm_provider=provider,
            llm_model=os.getenv("LLM_MODEL") or DEFAULT_MODELS.get(provider, ""),
            llm_key=llm_key,
            ollama_base_url=os.getenv("OLLAMA_BASE_URL", DEFAULT_OLLAMA_BASE_URL),
            gitlab_url=os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/"),
            gitlab_token=os.getenv("GITLAB_TOKEN", ""),
            gitlab_group_id=os.getenv("GITLAB_GROUP_ID", ""),
        )
