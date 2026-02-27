"""Merge request tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import Tool


class ListMergeRequestsTool(Tool):
    @property
    def name(self) -> str:
        return "list_merge_requests"

    @property
    def description(self) -> str:
        return "List merge requests in the project. Filter by state or search text."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["opened", "closed", "merged", "all"],
                    "description": "Filter by MR state",
                    "default": "opened",
                },
                "search": {
                    "type": "string",
                    "description": "Search MRs by title or description",
                    "default": "",
                },
            },
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        mrs = gitlab.list_merge_requests(
            state=kwargs.get("state", "opened"),
            search=kwargs.get("search", ""),
        )
        if not mrs:
            return "No merge requests found matching the criteria."

        lines = [f"Found {len(mrs)} merge request(s):\n"]
        for mr in mrs:
            author = mr.get("author", {}).get("username", "unknown")
            lines.append(
                f"  !{mr['iid']} [{mr['state']}] {mr['title']}"
                f"  by {author}"
                f"  {mr.get('source_branch', '?')} -> {mr.get('target_branch', '?')}"
            )
        return "\n".join(lines)


class GetMergeRequestTool(Tool):
    @property
    def name(self) -> str:
        return "get_merge_request"

    @property
    def description(self) -> str:
        return (
            "Get detailed information about a specific merge request,"
            " including its pipeline status."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mr_iid": {
                    "type": "integer",
                    "description": "The IID (number) of the merge request",
                },
            },
            "required": ["mr_iid"],
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        mr = gitlab.get_merge_request(kwargs["mr_iid"])

        author = mr.get("author", {}).get("username", "unknown")
        reviewers = ", ".join(r.get("username", "?") for r in mr.get("reviewers", []))
        assignees = ", ".join(a.get("username", "?") for a in mr.get("assignees", []))
        labels = ", ".join(mr.get("labels", []))

        pipeline = mr.get("head_pipeline") or {}
        pipeline_status = pipeline.get("status", "none")
        pipeline_url = pipeline.get("web_url", "N/A")

        # Try to get approval info
        approval_info = ""
        try:
            approvals = gitlab.get_merge_request_approvals(kwargs["mr_iid"])
            approved_by = ", ".join(
                a.get("user", {}).get("username", "?")
                for a in approvals.get("approved_by", [])
            )
            approval_info = (
                f"Approvals: {approvals.get('approvals_left', '?')} remaining"
                f"  Approved by: {approved_by or 'no one yet'}\n"
            )
        except Exception:
            pass

        return (
            f"MR !{mr['iid']}: {mr['title']}\n"
            f"State: {mr['state']}\n"
            f"Author: {author}\n"
            f"Assignees: {assignees or 'None'}\n"
            f"Reviewers: {reviewers or 'None'}\n"
            f"Labels: {labels or 'None'}\n"
            f"Branch: {mr.get('source_branch', '?')} -> {mr.get('target_branch', '?')}\n"
            f"Pipeline: {pipeline_status}\n"
            f"Pipeline URL: {pipeline_url}\n"
            f"{approval_info}"
            f"URL: {mr['web_url']}\n"
            f"\n{mr.get('description', '(no description)')}"
        )


class GetMergeRequestPipelinesTool(Tool):
    @property
    def name(self) -> str:
        return "get_merge_request_pipelines"

    @property
    def description(self) -> str:
        return "Get the list of pipelines for a specific merge request."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mr_iid": {
                    "type": "integer",
                    "description": "The IID of the merge request",
                },
            },
            "required": ["mr_iid"],
        }

    def run(self, gitlab: GitLabClient, **kwargs: Any) -> str:
        pipelines = gitlab.get_merge_request_pipelines(kwargs["mr_iid"])
        if not pipelines:
            return "No pipelines found for this merge request."

        lines = [f"Found {len(pipelines)} pipeline(s):\n"]
        for p in pipelines:
            lines.append(
                f"  #{p['id']} [{p['status']}] ref: {p.get('ref', '?')} "
                f"  {p.get('web_url', '')}"
            )
        return "\n".join(lines)
