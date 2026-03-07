"""Create a fully populated tool registry."""

from __future__ import annotations

from gitlab_agent.tools.base import ToolRegistry
from gitlab_agent.tools.boards import (
    ListBoardColumnsTool,
    ListBoardsTool,
    MoveIssueToBoardColumnTool,
)
from gitlab_agent.tools.groups import GetGroupInfoTool, ListGroupProjectsTool
from gitlab_agent.tools.issues import (
    CloseIssueTool,
    CreateIssueTool,
    GetIssueTool,
    ListIssuesTool,
    UpdateIssueTool,
)
from gitlab_agent.tools.labels import CreateLabelTool, ListLabelsTool
from gitlab_agent.tools.merge_requests import (
    GetMergeRequestPipelinesTool,
    GetMergeRequestTool,
    ListMergeRequestsTool,
)
from gitlab_agent.tools.search import ListMilestonesTool, SearchProjectTool


def create_default_registry() -> ToolRegistry:
    """Instantiate and register all built-in tools."""
    registry = ToolRegistry()

    # Issues
    registry.register(CreateIssueTool())
    registry.register(ListIssuesTool())
    registry.register(GetIssueTool())
    registry.register(UpdateIssueTool())
    registry.register(CloseIssueTool())

    # Labels
    registry.register(ListLabelsTool())
    registry.register(CreateLabelTool())

    # Merge Requests
    registry.register(ListMergeRequestsTool())
    registry.register(GetMergeRequestTool())
    registry.register(GetMergeRequestPipelinesTool())

    # Boards
    registry.register(ListBoardsTool())
    registry.register(ListBoardColumnsTool())
    registry.register(MoveIssueToBoardColumnTool())

    # Search & Milestones
    registry.register(SearchProjectTool())
    registry.register(ListMilestonesTool())

    # Groups
    registry.register(GetGroupInfoTool())
    registry.register(ListGroupProjectsTool())

    return registry
