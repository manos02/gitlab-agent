"""CLI chat interface – the user-facing entry point."""

from __future__ import annotations
import asyncio

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.theme import Theme

from gitlab_agent.agent import Agent
from gitlab_agent.config import Config

# Custom theme
theme = Theme(
    {
        "info": "cyan",
        "warning": "yellow",
        "error": "bold red",
        "tool": "dim cyan",
    }
)
console = Console(theme=theme)


def _on_tool_call(name: str, args: dict) -> None:
    """
    Display tool calls as they happen.
    e.g.
    ⚙ set_active_project(project_id_or_path='group/project')
    ⚙ list_issues(labels='bug', state='opened')
    """
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"  [tool]⚙ {name}({args_str})[/tool]")


async def _run() -> None:
    """Run the CLI chat loop."""
    console.print(
        Panel.fit(
            "[bold cyan]GitLab Agent[/bold cyan]\n"
            "An AI assistant for managing GitLab through a FastMCP server.\n"
            "Type [bold]/help[/bold] for commands, [bold]/q[/bold] to exit.",
            border_style="cyan",
        )
    )

    # Load config
    config = Config.from_env()
    console.print(f"[info]Provider: {config.llm_provider} ({config.llm_model})[/info]")
    if config.gitlab_group_id:
        console.print(
            f"[info]GitLab: {config.gitlab_url} (group {config.gitlab_group_id})[/info]"
        )
    else:
        console.print(
            f"[warning]GitLab: {config.gitlab_url} (no project/group selected)[/warning]"
        )
        console.print("[info]Tip: use /group <id-or-path> or /project <id-or-path>.[/info]")
    console.print()

    agent = Agent(config, on_tool_call=_on_tool_call)
    await agent.open()
    console.print(f"[info]{await agent.get_active_scope()}[/info]")
    console.print()

    try:
        while True:
            try:
                user_input = console.input("[bold green]You>[/bold green] ").strip()
            except (EOFError, KeyboardInterrupt):
                console.print("\n[info]Goodbye![/info]")
                break

            if not user_input:
                continue

            # Handle slash commands
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd in ("/quit", "/exit", "/q"):
                    console.print("[info]Goodbye![/info]")
                    break
                elif cmd in ("/reset", "/clear"):
                    agent.reset()
                    console.print("[info]Conversation cleared.[/info]\n")
                    continue
                elif cmd.startswith("/group"):
                    value = user_input[len("/group"):].strip()
                    if not value:
                        console.print(f"[info]{await agent.get_active_scope()}[/info]\n")
                        continue

                    try:
                        result = await agent.set_group(value)
                    except ValueError as e:
                        console.print(f"[error]{e}[/error]\n")
                        continue

                    console.print(f"[info]{result}[/info]\n")
                    continue
                elif cmd.startswith("/project"):
                    value = user_input[len("/project"):].strip()
                    if not value:
                        console.print(f"[info]{await agent.get_active_scope()}[/info]\n")
                        continue

                    try:
                        result = await agent.set_project(value)
                    except ValueError as e:
                        console.print(f"[error]{e}[/error]\n")
                        continue

                    console.print(f"[info]{result}[/info]\n")
                    continue
                elif cmd == "/clear-project":
                    console.print(f"[info]{await agent.clear_project()}[/info]\n")
                    continue
                elif cmd.startswith("/projects"):
                    search = user_input[len("/projects"):].strip()
                    try:
                        result = await agent.list_group_projects(search=search)
                    except RuntimeError as e:
                        console.print(f"[error]{e}[/error]\n")
                        continue

                    console.print(Markdown(result))
                    console.print()
                    continue
                elif cmd == "/catalog":
                    try:
                        result = await agent.get_project_catalog(refresh=True, limit=200)
                    except RuntimeError as e:
                        console.print(f"[error]{e}[/error]\n")
                        continue

                    console.print(Markdown(result))
                    console.print()
                    continue
                elif cmd in ("/help", "/h"):
                    console.print(
                        Panel(
                            "[bold]/quit[/bold]  – Exit the agent\n"
                            "[bold]/reset[/bold] – Clear conversation history\n"
                            "[bold]/group <id-or-path>[/bold] – Set active GitLab group\n"
                            "[bold]/project <id-or-path>[/bold] – Set active GitLab project\n"
                            "[bold]/clear-project[/bold] – Clear active project scope\n"
                            "[bold]/projects [search][/bold] – List projects in the active group\n"
                            "[bold]/catalog[/bold] – Refresh and show the cached project catalog\n"
                            "[bold]/help[/bold]  – Show this help\n"
                            "[dim]Scope is stored in the MCP session and reused across tool calls.[/dim]\n"
                            "\nJust type naturally to interact with GitLab:\n"
                            '  "Create a bug ticket about the login page crashing"\n'
                            '  "Find the MR related to the search feature"\n'
                            '  "List all open issues with the \'urgent\' label"',
                            title="Commands",
                            border_style="cyan",
                        )
                    )
                    continue
                else:
                    console.print(f"[warning]Unknown command: {cmd}[/warning]")
                    continue

            # Send to agent
            try:
                with console.status("[info]Thinking...[/info]", spinner="dots"):
                    response = await agent.chat(user_input)
            except RuntimeError as e:
                console.print(f"\n[error]{e}[/error]\n")
                continue

            console.print()
            console.print(Markdown(response))
            console.print()

    finally:
        await agent.close()


def main() -> None:
    asyncio.run(_run())


if __name__ == "__main__":
    main()
