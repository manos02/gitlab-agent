"""Project alias helpers.

Alias initialization is currently disabled while API tools are rebuilt.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gitlab_agent.gitlab_client import GitLabClient


def fetch_project_aliases(gitlab: "GitLabClient") -> dict[str, str]:
    """Return no aliases while endpoint wrappers are being rebuilt."""
    _ = gitlab
    return {}
