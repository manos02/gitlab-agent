"""Factory for creating the configured LLM provider."""

from __future__ import annotations

from gitlab_agent.config import Config
from gitlab_agent.llm.base import BaseLLMProvider


def create_llm_provider(config: Config) -> BaseLLMProvider:
    """Instantiate the LLM provider specified in config."""
    if config.llm_provider == "openai":
        from gitlab_agent.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(config)
    elif config.llm_provider == "anthropic":
        from gitlab_agent.llm.anthropic_provider import AnthropicProvider
        return AnthropicProvider(config)
    elif config.llm_provider == "google":
        from gitlab_agent.llm.google_provider import GoogleProvider
        return GoogleProvider(config)
    elif config.llm_provider == "ollama":
        from gitlab_agent.llm.openai_provider import OpenAIProvider
        return OpenAIProvider(
            config,
            base_url=config.ollama_base_url,
            api_key="ollama",  # Ollama doesn't need a real key but the client requires one
        )
    else:
        raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
