"""Create the tool registry.

Currently empty by design so API tools can be rebuilt from scratch.
"""

from __future__ import annotations

from gitlab_agent.tools.base import ToolRegistry


def create_default_registry() -> ToolRegistry:
    """Instantiate the default registry.

    No tools are registered so endpoint wrappers can be reintroduced cleanly.
    """
    registry = ToolRegistry()

    return registry
