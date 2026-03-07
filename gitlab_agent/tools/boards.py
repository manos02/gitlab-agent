"""Board management tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class ListBoardsTool(JsonTool):
    tool_name = "list_boards"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        boards = gitlab.list_boards()
        if not boards:
            return "No boards found in the active scope."

        lines = [f"Found {len(boards)} board(s):\n"]
        for board in boards:
            lists_info = ""
            try:
                board_lists = gitlab.list_board_lists(board["id"])
                list_names = [
                    bl.get("label", {}).get("name", f"list-{bl['id']}")
                    for bl in board_lists
                ]
                lists_info = f"  Columns: {', '.join(list_names)}" if list_names else ""
            except Exception:
                pass
            lines.append(f"  Board #{board['id']}: {board.get('name', 'Default')}{lists_info}")
        return "\n".join(lines)


class ListBoardColumnsTool(JsonTool):
    tool_name = "list_board_columns"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        board_lists = gitlab.list_board_lists(kwargs["board_id"])
        if not board_lists:
            return "No columns found on this board."

        lines = [f"Found {len(board_lists)} column(s):\n"]
        for bl in board_lists:
            label = bl.get("label", {})
            name = label.get("name", f"list-{bl['id']}")
            position = bl.get("position", "?")
            lines.append(f"  [{position}] {name} (list ID: {bl['id']})")
        return "\n".join(lines)


class MoveIssueToBoardColumnTool(JsonTool):
    """Move an issue to a board column by adding/removing the column label.

    GitLab boards work via labels — each column is mapped to a label.
    Moving an issue to a column means applying that column's label.
    """

    tool_name = "move_issue_to_board_column"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issue_iid = kwargs["issue_iid"]
        column_label = kwargs["column_label"]

        # Get current issue to preserve existing labels
        issue = gitlab.get_issue(issue_iid)
        current_labels = set(issue.get("labels", []))
        current_labels.add(column_label)

        updated = gitlab.update_issue(issue_iid, labels=",".join(current_labels))
        return (
            f"Issue #{updated['iid']} moved to '{column_label}' column. "
            f"Current labels: {', '.join(updated.get('labels', []))}"
        )
