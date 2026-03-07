"""Search tools for finding issues, MRs, and more."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class SearchProjectTool(JsonTool):
    tool_name = "search_project"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        results = gitlab.search_project(kwargs["scope"], kwargs["search"])
        if not results:
            return f"No {kwargs['scope']} found matching '{kwargs['search']}'."

        scope = kwargs["scope"]
        lines = [f"Found {len(results)} {scope} matching '{kwargs['search']}':\n"]

        for item in results[:20]:  # cap display
            if scope == "issues":
                lines.append(f"  #{item['iid']} [{item['state']}] {item['title']}")
            elif scope == "merge_requests":
                lines.append(f"  !{item['iid']} [{item['state']}] {item['title']}")
            elif scope == "milestones":
                lines.append(f"  {item['title']} [{item.get('state', '?')}]")
            else:
                lines.append(f"  {item.get('title', item.get('filename', str(item)[:80]))}")

        return "\n".join(lines)


class ListMilestonesTool(JsonTool):
    tool_name = "list_milestones"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        milestones = gitlab.list_milestones(state=kwargs.get("state", "active"))
        if not milestones:
            return "No milestones found."

        lines = [f"Found {len(milestones)} milestone(s):\n"]
        for ms in milestones:
            due = ms.get("due_date", "no due date")
            lines.append(f"  {ms['title']} [{ms['state']}] due: {due}")
        return "\n".join(lines)
