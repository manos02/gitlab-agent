"""Issue-related tools: create, list, get, update, close."""

from __future__ import annotations

import json
from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import Tool


class CreateIssueTool(Tool):
    @property
    def name(self) -> str:
        return "create_issue"

    @property
    def description(self) -> str:
        return (
            "Create a new issue in the GitLab project. "
            "You can set a title, description, labels (comma-separated), and assignees."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the issue",
                },
                "description": {
                    "type": "string",
                    "description": "Markdown body of the issue",
                    "default": "",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated label names, e.g. 'bug,urgent'",
                    "default": "",
                },
            },
            "required": ["title"],
        }

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


class ListIssuesTool(Tool):
    @property
    def name(self) -> str:
        return "list_issues"

    @property
    def description(self) -> str:
        return (
            "List issues in the project. Can filter by state (opened/closed/all), "
            "labels, search text, or milestone."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["opened", "closed", "all"],
                    "description": "Filter by issue state",
                    "default": "opened",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated labels to filter by",
                    "default": "",
                },
                "search": {
                    "type": "string",
                    "description": "Search issues by title or description",
                    "default": "",
                },
                "milestone": {
                    "type": "string",
                    "description": "Filter by milestone title",
                    "default": "",
                },
            },
        }

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


class GetIssueTool(Tool):
    @property
    def name(self) -> str:
        return "get_issue"

    @property
    def description(self) -> str:
        return "Get detailed information about a specific issue by its IID (issue number)."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_iid": {
                    "type": "integer",
                    "description": "The IID (number) of the issue",
                },
            },
            "required": ["issue_iid"],
        }

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


class UpdateIssueTool(Tool):
    @property
    def name(self) -> str:
        return "update_issue"

    @property
    def description(self) -> str:
        return (
            "Update an existing issue. Can change title, description, labels, or state."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_iid": {
                    "type": "integer",
                    "description": "The IID (number) of the issue to update",
                },
                "title": {
                    "type": "string",
                    "description": "New title",
                },
                "description": {
                    "type": "string",
                    "description": "New description (Markdown)",
                },
                "labels": {
                    "type": "string",
                    "description": "New comma-separated labels (replaces existing)",
                },
                "state_event": {
                    "type": "string",
                    "enum": ["close", "reopen"],
                    "description": "Change issue state",
                },
            },
            "required": ["issue_iid"],
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        iid = kwargs.pop("issue_iid")
        # Only pass fields that were provided
        fields = {k: v for k, v in kwargs.items() if v is not None and v != ""}
        issue = gitlab.update_issue(iid, **fields)
        return f"Issue #{issue['iid']} updated. State: {issue['state']}, URL: {issue['web_url']}"


class CloseIssueTool(Tool):
    @property
    def name(self) -> str:
        return "close_issue"

    @property
    def description(self) -> str:
        return "Close an issue by its IID."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "issue_iid": {
                    "type": "integer",
                    "description": "The IID (number) of the issue to close",
                },
            },
            "required": ["issue_iid"],
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        issue = gitlab.close_issue(kwargs["issue_iid"])
        return f"Issue #{issue['iid']} is now closed."
