"""FastMCP server exposing GitLab tools."""

from __future__ import annotations

from functools import lru_cache

from fastmcp import Context, FastMCP

from gitlab_agent import __version__
from gitlab_agent.config import Config
from gitlab_agent.gitlab_client import GitLabClient


SERVER_INSTRUCTIONS = """This server exposes GitLab issue, merge request, board, search, label, and group tools.

Use set_active_group to choose a default group scope.
Use set_active_project when a task requires project-scoped operations like creating issues or reading labels.
Listing and search tools prefer the active project and fall back to the active group when possible.
Use get_active_scope to inspect the current MCP session scope.
"""

ACTIVE_GROUP_KEY = "active_group"
ACTIVE_PROJECT_KEY = "active_project"

mcp = FastMCP(
    name="GitLab Agent",
    instructions=SERVER_INSTRUCTIONS,
    version=__version__,
)


@lru_cache(maxsize=1)
def _load_config() -> Config:
    return Config.from_env()


async def _client_from_context(ctx: Context) -> GitLabClient:
    client = GitLabClient(_load_config())
    active_group = await ctx.get_state(ACTIVE_GROUP_KEY)
    active_project = await ctx.get_state(ACTIVE_PROJECT_KEY)
    if active_group:
        client.set_group(active_group)
    if active_project:
        client.set_project(active_project)
    return client


async def _current_scope(ctx: Context) -> tuple[str | None, str | None]:
    client = await _client_from_context(ctx)
    try:
        return client.current_project(), client.current_group()
    finally:
        client.close()


def _labels_text(values: list[str]) -> str:
    return ", ".join(values) if values else "None"


@mcp.tool
async def get_active_scope(ctx: Context) -> str:
    """Show the active project and group for the current MCP session."""
    active_project, active_group = await _current_scope(ctx)
    return (
        f"Active project: {active_project or 'None'}\n"
        f"Active group: {active_group or 'None'}"
    )


@mcp.tool
async def set_active_group(group_id_or_path: str, ctx: Context) -> str:
    """Set the active GitLab group for the current MCP session."""
    value = group_id_or_path.strip()
    if not value:
        raise ValueError("Group cannot be empty")

    await ctx.set_state(ACTIVE_GROUP_KEY, value)
    await ctx.delete_state(ACTIVE_PROJECT_KEY)
    return f"Active group set to: {value}. Active project cleared."


@mcp.tool
async def set_active_project(project_id_or_path: str, ctx: Context) -> str:
    """Set the active GitLab project for the current MCP session."""
    value = project_id_or_path.strip()
    if not value:
        raise ValueError("Project cannot be empty")

    await ctx.set_state(ACTIVE_PROJECT_KEY, value)
    return f"Active project set to: {value}"


@mcp.tool
async def clear_active_project(ctx: Context) -> str:
    """Clear the active GitLab project for the current MCP session."""
    await ctx.delete_state(ACTIVE_PROJECT_KEY)
    return "Active project cleared."


@mcp.tool
async def create_issue(title: str, description: str = "", labels: str = "", ctx: Context | None = None) -> str:
    """Create a new issue in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        issue = gitlab.create_issue(title=title, description=description, labels=labels)
    finally:
        gitlab.close()
    return f"Issue #{issue['iid']} created: {issue['title']}\nURL: {issue['web_url']}"


@mcp.tool
async def list_issues(
    state: str = "opened",
    labels: str = "",
    search: str = "",
    milestone: str = "",
    ctx: Context | None = None,
) -> str:
    """List issues in the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        issues = gitlab.list_issues(state=state, labels=labels, search=search, milestone=milestone)
    finally:
        gitlab.close()

    if not issues:
        return "No issues found matching the criteria."

    lines = [f"Found {len(issues)} issue(s):\n"]
    for issue in issues:
        issue_labels = ", ".join(issue.get("labels", []))
        assignees = ", ".join(a["username"] for a in issue.get("assignees", []))
        ref = issue.get("references", {}).get("full") or f"#{issue['iid']}"
        lines.append(
            f"  {ref} [{issue['state']}] {issue['title']}"
            + (f"  labels: {issue_labels}" if issue_labels else "")
            + (f"  assignees: {assignees}" if assignees else "")
        )
    return "\n".join(lines)


@mcp.tool
async def get_issue(issue_iid: int, ctx: Context | None = None) -> str:
    """Get a single issue from the active project by IID."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        issue = gitlab.get_issue(issue_iid)
    finally:
        gitlab.close()

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
        f"URL: {issue['web_url']}\n\n"
        f"{issue.get('description', '(no description)')}"
    )


@mcp.tool
async def update_issue(
    issue_iid: int,
    title: str = "",
    description: str = "",
    labels: str = "",
    state_event: str = "",
    ctx: Context | None = None,
) -> str:
    """Update fields on an issue in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        fields = {
            key: value
            for key, value in {
                "title": title,
                "description": description,
                "labels": labels,
                "state_event": state_event,
            }.items()
            if value != ""
        }
        issue = gitlab.update_issue(issue_iid, **fields)
    finally:
        gitlab.close()
    return f"Issue #{issue['iid']} updated. State: {issue['state']}, URL: {issue['web_url']}"


@mcp.tool
async def close_issue(issue_iid: int, ctx: Context | None = None) -> str:
    """Close an issue in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        issue = gitlab.close_issue(issue_iid)
    finally:
        gitlab.close()
    return f"Issue #{issue['iid']} is now closed."


@mcp.tool
async def list_labels(ctx: Context | None = None) -> str:
    """List labels in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        labels = gitlab.list_labels()
    finally:
        gitlab.close()
    if not labels:
        return "No labels found in this project."
    lines = [f"Found {len(labels)} label(s):\n"]
    for label in labels:
        lines.append(f"  - {label['name']} ({label['color']}): {label.get('description', '')}")
    return "\n".join(lines)


@mcp.tool
async def create_label(
    name: str,
    color: str = "#428BCA",
    description: str = "",
    ctx: Context | None = None,
) -> str:
    """Create a label in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        label = gitlab.create_label(name=name, color=color, description=description)
    finally:
        gitlab.close()
    return f"Label '{label['name']}' created with color {label['color']}."


@mcp.tool
async def list_merge_requests(
    state: str = "opened",
    search: str = "",
    ctx: Context | None = None,
) -> str:
    """List merge requests in the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        merge_requests = gitlab.list_merge_requests(state=state, search=search)
    finally:
        gitlab.close()
    if not merge_requests:
        return "No merge requests found matching the criteria."

    lines = [f"Found {len(merge_requests)} merge request(s):\n"]
    for merge_request in merge_requests:
        author = merge_request.get("author", {}).get("username", "unknown")
        ref = merge_request.get("references", {}).get("full") or f"!{merge_request['iid']}"
        lines.append(
            f"  {ref} [{merge_request['state']}] {merge_request['title']}"
            f"  by {author}"
            f"  {merge_request.get('source_branch', '?')} -> {merge_request.get('target_branch', '?')}"
        )
    return "\n".join(lines)


@mcp.tool
async def get_merge_request(mr_iid: int, ctx: Context | None = None) -> str:
    """Get a merge request from the active project by IID."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        merge_request = gitlab.get_merge_request(mr_iid)
        try:
            approvals = gitlab.get_merge_request_approvals(mr_iid)
        except Exception:
            approvals = None
    finally:
        gitlab.close()

    author = merge_request.get("author", {}).get("username", "unknown")
    reviewers = ", ".join(r.get("username", "?") for r in merge_request.get("reviewers", []))
    assignees = ", ".join(a.get("username", "?") for a in merge_request.get("assignees", []))
    labels = ", ".join(merge_request.get("labels", []))
    pipeline = merge_request.get("head_pipeline") or {}
    approval_info = ""
    if approvals is not None:
        approved_by = ", ".join(
            item.get("user", {}).get("username", "?")
            for item in approvals.get("approved_by", [])
        )
        approval_info = (
            f"Approvals: {approvals.get('approvals_left', '?')} remaining"
            f"  Approved by: {approved_by or 'no one yet'}\n"
        )
    return (
        f"MR !{merge_request['iid']}: {merge_request['title']}\n"
        f"State: {merge_request['state']}\n"
        f"Author: {author}\n"
        f"Assignees: {assignees or 'None'}\n"
        f"Reviewers: {reviewers or 'None'}\n"
        f"Labels: {labels or 'None'}\n"
        f"Branch: {merge_request.get('source_branch', '?')} -> {merge_request.get('target_branch', '?')}\n"
        f"Pipeline: {pipeline.get('status', 'none')}\n"
        f"Pipeline URL: {pipeline.get('web_url', 'N/A')}\n"
        f"{approval_info}"
        f"URL: {merge_request['web_url']}\n\n"
        f"{merge_request.get('description', '(no description)')}"
    )


@mcp.tool
async def get_merge_request_pipelines(mr_iid: int, ctx: Context | None = None) -> str:
    """List pipelines for a merge request in the active project."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        pipelines = gitlab.get_merge_request_pipelines(mr_iid)
    finally:
        gitlab.close()
    if not pipelines:
        return "No pipelines found for this merge request."
    lines = [f"Found {len(pipelines)} pipeline(s):\n"]
    for pipeline in pipelines:
        lines.append(
            f"  #{pipeline['id']} [{pipeline['status']}] ref: {pipeline.get('ref', '?')}  {pipeline.get('web_url', '')}"
        )
    return "\n".join(lines)


@mcp.tool
async def list_boards(ctx: Context | None = None) -> str:
    """List boards in the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        boards = gitlab.list_boards()
        if not boards:
            return "No boards found in the active scope."

        lines = [f"Found {len(boards)} board(s):\n"]
        for board in boards:
            lists_info = ""
            try:
                board_lists = gitlab.list_board_lists(board["id"])
                list_names = [
                    board_list.get("label", {}).get("name", f"list-{board_list['id']}")
                    for board_list in board_lists
                ]
                lists_info = f"  Columns: {', '.join(list_names)}" if list_names else ""
            except Exception:
                pass
            lines.append(
                f"  Board #{board['id']}: {board.get('name', 'Default')}{lists_info}"
            )
        return "\n".join(lines)
    finally:
        gitlab.close()


@mcp.tool
async def list_board_columns(board_id: int, ctx: Context | None = None) -> str:
    """List columns for a board in the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        board_lists = gitlab.list_board_lists(board_id)
    finally:
        gitlab.close()
    if not board_lists:
        return "No columns found on this board."

    lines = [f"Found {len(board_lists)} column(s):\n"]
    for board_list in board_lists:
        label = board_list.get("label", {})
        name = label.get("name", f"list-{board_list['id']}")
        position = board_list.get("position", "?")
        lines.append(f"  [{position}] {name} (list ID: {board_list['id']})")
    return "\n".join(lines)


@mcp.tool
async def move_issue_to_board_column(
    issue_iid: int,
    column_label: str,
    ctx: Context | None = None,
) -> str:
    """Move an issue to a board column by applying the column label."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        issue = gitlab.get_issue(issue_iid)
        current_labels = set(issue.get("labels", []))
        current_labels.add(column_label)
        updated = gitlab.update_issue(issue_iid, labels=",".join(sorted(current_labels)))
    finally:
        gitlab.close()
    return (
        f"Issue #{updated['iid']} moved to '{column_label}' column. "
        f"Current labels: {_labels_text(updated.get('labels', []))}"
    )


@mcp.tool
async def search_project(scope: str, search: str, ctx: Context | None = None) -> str:
    """Search the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        results = gitlab.search_project(scope, search)
    finally:
        gitlab.close()
    if not results:
        return f"No {scope} found matching '{search}'."

    lines = [f"Found {len(results)} {scope} matching '{search}':\n"]
    for item in results[:20]:
        if scope == "issues":
            lines.append(f"  #{item['iid']} [{item['state']}] {item['title']}")
        elif scope == "merge_requests":
            lines.append(f"  !{item['iid']} [{item['state']}] {item['title']}")
        elif scope == "milestones":
            lines.append(f"  {item['title']} [{item.get('state', '?')}]")
        else:
            lines.append(f"  {item.get('title', item.get('filename', str(item)[:80]))}")
    return "\n".join(lines)


@mcp.tool
async def list_milestones(state: str = "active", ctx: Context | None = None) -> str:
    """List milestones in the active project or group scope."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        milestones = gitlab.list_milestones(state=state)
    finally:
        gitlab.close()
    if not milestones:
        return "No milestones found."
    lines = [f"Found {len(milestones)} milestone(s):\n"]
    for milestone in milestones:
        due = milestone.get("due_date", "no due date")
        lines.append(f"  {milestone['title']} [{milestone['state']}] due: {due}")
    return "\n".join(lines)


@mcp.tool
async def get_group_info(ctx: Context | None = None) -> str:
    """Get metadata for the active group."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        group = gitlab.get_group()
    finally:
        gitlab.close()
    visibility = group.get("visibility", "unknown")
    full_path = group.get("full_path", group.get("path", "?"))
    web_url = group.get("web_url", "")
    return (
        f"Group: {group.get('name', '?')}\n"
        f"Path: {full_path}\n"
        f"Visibility: {visibility}\n"
        f"Web URL: {web_url}\n"
        f"Description: {group.get('description') or '(none)'}"
    )


@mcp.tool
async def list_group_projects(
    search: str = "",
    include_subgroups: bool = True,
    ctx: Context | None = None,
) -> str:
    """List projects in the active group."""
    if ctx is None:
        raise RuntimeError("Context is required")
    gitlab = await _client_from_context(ctx)
    try:
        projects = gitlab.list_group_projects(
            search=search,
            include_subgroups=include_subgroups,
        )
    finally:
        gitlab.close()
    if not projects:
        return "No group projects found."

    lines = [f"Found {len(projects)} group project(s):\n"]
    for project in projects[:30]:
        lines.append(
            f"  {project.get('name_with_namespace', project.get('name', '?'))}"
            f"  id: {project.get('id', '?')}"
            f"  path: {project.get('path_with_namespace', '?')}"
        )
    return "\n".join(lines)


def main() -> None:
    """Run the FastMCP server over stdio."""
    mcp.run()


if __name__ == "__main__":
    main()