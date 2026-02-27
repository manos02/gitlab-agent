"""Configuration loaded from environment variables / .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# Default models per provider
DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o",
    "anthropic": "claude-sonnet-4-20250514",
    "google": "gemini-2.0-flash",
}


@dataclass(frozen=True)
class Config:
    """Immutable application configuration."""

    # LLM
    llm_provider: str
    llm_model: str
    openai_api_key: str | None = field(default=None, repr=False)
    anthropic_api_key: str | None = field(default=None, repr=False)
    google_api_key: str | None = field(default=None, repr=False)

    # GitLab
    gitlab_url: str = "https://gitlab.com"
    gitlab_token: str = field(default="", repr=False)
    gitlab_project_id: str = ""

    @classmethod
    def from_env(cls, env_path: str | Path | None = None) -> Config:
        """Load configuration from environment variables (with optional .env file)."""
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()  # searches CWD and parents

        provider = os.getenv("LLM_PROVIDER", "openai").lower().strip()
        model = os.getenv("LLM_MODEL", "") or DEFAULT_MODELS.get(provider, "")

        return cls(
            llm_provider=provider,
            llm_model=model,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            gitlab_url=os.getenv("GITLAB_URL", "https://gitlab.com").rstrip("/"),
            gitlab_token=os.getenv("GITLAB_TOKEN", ""),
            gitlab_project_id=os.getenv("GITLAB_PROJECT_ID", ""),
        )

    def validate(self) -> list[str]:
        """Return a list of configuration problems (empty = valid)."""
        problems: list[str] = []

        if self.llm_provider not in DEFAULT_MODELS:
            problems.append(
                f"LLM_PROVIDER must be one of {list(DEFAULT_MODELS.keys())}, "
                f"got '{self.llm_provider}'"
            )

        key_map = {
            "openai": self.openai_api_key,
            "anthropic": self.anthropic_api_key,
            "google": self.google_api_key,
        }
        if not key_map.get(self.llm_provider):
            env_var = f"{self.llm_provider.upper()}_API_KEY"
            problems.append(f"{env_var} is required when LLM_PROVIDER={self.llm_provider}")

        if not self.gitlab_token:
            problems.append("GITLAB_TOKEN is required")

        if not self.gitlab_project_id:
            problems.append("GITLAB_PROJECT_ID is required")

        return problems
