"""Issue-related tools: create, list, get, update, close."""

from __future__ import annotations

import json
from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class CreateIssueTool(JsonTool):
    tool_name = "create_issue"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issue = gitlab.create_issue(
            title=kwargs["title"],
            description=kwargs.get("description", ""),
            labels=kwargs.get("labels", ""),
        )
        return (
            f"Issue #{issue['iid']} created: {issue['title']}\n"
            f"URL: {issue['web_url']}"
        )


class ListIssuesTool(JsonTool):
    tool_name = "list_issues"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issues = gitlab.list_issues(
            state=kwargs.get("state", "opened"),
            labels=kwargs.get("labels", ""),
            search=kwargs.get("search", ""),
            milestone=kwargs.get("milestone", ""),
        )
        if not issues:
            return "No issues found matching the criteria."

        lines = [f"Found {len(issues)} issue(s):\n"]
        for issue in issues:
            labels = ", ".join(issue.get("labels", []))
            assignees = ", ".join(a["username"] for a in issue.get("assignees", []))
            ref = issue.get("references", {}).get("full") or f"#{issue['iid']}"
            lines.append(
                f"  {ref} [{issue['state']}] {issue['title']}"
                + (f"  labels: {labels}" if labels else "")
                + (f"  assignees: {assignees}" if assignees else "")
            )
        return "\n".join(lines)


class GetIssueTool(JsonTool):
    tool_name = "get_issue"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issue = gitlab.get_issue(kwargs["issue_iid"])
        labels = ", ".join(issue.get("labels", []))
        assignees = ", ".join(a["username"] for a in issue.get("assignees", []))
        milestone = issue.get("milestone", {})
        milestone_title = milestone.get("title", "None") if milestone else "None"

        return (
            f"Issue #{issue['iid']}: {issue['title']}\n"
            f"State: {issue['state']}\n"
            f"Labels: {labels or 'None'}\n"
            f"Assignees: {assignees or 'Unassigned'}\n"
            f"Milestone: {milestone_title}\n"
            f"URL: {issue['web_url']}\n"
            f"\n{issue.get('description', '(no description)')}"
        )


class UpdateIssueTool(JsonTool):
    tool_name = "update_issue"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        iid = kwargs.pop("issue_iid")
        # Only pass fields that were provided
        fields = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        issue = gitlab.update_issue(iid, **fields)
        return f"Issue #{issue['iid']} updated. State: {issue['state']}, URL: {issue['web_url']}"


class CloseIssueTool(JsonTool):
    tool_name = "close_issue"

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issue = gitlab.close_issue(kwargs["issue_iid"])
        return f"Issue #{issue['iid']} is now closed."
