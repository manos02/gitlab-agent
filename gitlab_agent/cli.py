"""CLI chat interface – the user-facing entry point."""

from __future__ import annotations

import sys

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
    """Display tool calls as they happen."""
    args_str = ", ".join(f"{k}={v!r}" for k, v in args.items())
    console.print(f"  [tool]⚙ {name}({args_str})[/tool]")


def main() -> None:
    """Run the CLI chat loop."""
    console.print(
        Panel.fit(
            "[bold cyan]GitLab Agent[/bold cyan]\n"
            "An AI assistant for managing your GitLab project.\n"
            "Type [bold]/help[/bold] for commands, [bold]/quit[/bold] to exit.",
            border_style="cyan",
        )
    )

    # Load config
    config = Config.from_env()
    problems = config.validate()
    if problems:
        console.print("[error]Configuration errors:[/error]")
        for p in problems:
            console.print(f"  [error]• {p}[/error]")
        console.print("\nPlease set up your [bold].env[/bold] file. See [bold].env.example[/bold].")
        sys.exit(1)

    console.print(
        f"[info]Provider: {config.llm_provider} ({config.llm_model})[/info]"
    )
    console.print(
        f"[info]GitLab: {config.gitlab_url} (project {config.gitlab_project_id})[/info]\n"
    )

    agent = Agent(config, on_tool_call=_on_tool_call)

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
                elif cmd in ("/help", "/h"):
                    console.print(
                        Panel(
                            "[bold]/quit[/bold]  – Exit the agent\n"
                            "[bold]/reset[/bold] – Clear conversation history\n"
                            "[bold]/help[/bold]  – Show this help\n"
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
            with console.status("[info]Thinking...[/info]", spinner="dots"):
                response = agent.chat(user_input)

            console.print()
            console.print(Markdown(response))
            console.print()

    finally:
        agent.close()


if __name__ == "__main__":
    main()
