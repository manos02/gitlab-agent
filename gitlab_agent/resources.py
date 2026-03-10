"""Helpers for loading packaged JSON resources."""

from __future__ import annotations

import json
from functools import lru_cache
from importlib.resources import files
from typing import Any


@lru_cache(maxsize=None)
def load_json_resource(resource_name: str) -> Any:
    """Load a JSON resource bundled inside the package."""
    resource_path = files("gitlab_agent").joinpath("data", resource_name)
    with resource_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=None)
def get_llm_defaults() -> dict[str, Any]:
    return load_json_resource("llm_defaults.json")
