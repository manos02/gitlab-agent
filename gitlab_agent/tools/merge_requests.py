"""Merge request tools."""

from __future__ import annotations

from typing import Any

from gitlab_agent.gitlab_client import GitLabClient
from gitlab_agent.tools.base import JsonTool


class ListMergeRequestsTool(JsonTool):
    tool_name = "list_merge_requests"

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
            ref = mr.get("references", {}).get("full") or f"!{mr['iid']}"
            lines.append(
                f"  {ref} [{mr['state']}] {mr['title']}"
                f"  by {author}"
                f"  {mr.get('source_branch', '?')} -> {mr.get('target_branch', '?')}"
            )
        return "\n".join(lines)


class GetMergeRequestTool(JsonTool):
    tool_name = "get_merge_request"

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


class GetMergeRequestPipelinesTool(JsonTool):
    tool_name = "get_merge_request_pipelines"

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
