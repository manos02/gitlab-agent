# GitLab Agent

An open-source GitLab assistant built around a FastMCP server, with an optional CLI chat client for local models and hosted APIs.

## What can it do?

Talk to your GitLab project like you'd talk to a teammate:

- **"Create a bug ticket about the login page crashing"** → Creates an issue with the `bug` label
- **"Find the ticket about the search feature"** → Searches issues by keyword
- **"Create 3 tickets for X, Y, Z and put them in the Sprint column"** → Creates issues and moves them to the right board column
- **"What's the status of the MR for ticket #42?"** → Shows MR details, pipeline status, approvals
- **"List all open issues with the urgent label"** → Filters and lists issues
- **"Close issue #15"** → Closes the issue

You can use it in three ways:

- As a FastMCP server from VS Code, Claude Code, or any MCP client
- As a local CLI chat assistant backed by OpenAI, Anthropic, Google, or Ollama-compatible models such as Qwen
- As a reusable Python MCP server that other tools can call directly

## Supported LLM Providers

| Provider  | Models                             | Env Variable        |
| --------- | ---------------------------------- | ------------------- |
| Google    | Gemini 2.0 Flash, Pro, etc.        | `GOOGLE_API_KEY`    |
| OpenAI    | GPT-4o, GPT-4, etc.                | `OPENAI_API_KEY`    |
| Anthropic | Claude Sonnet, Opus, etc.          | `ANTHROPIC_API_KEY` |
| Ollama    | Qwen 2.5, Llama 3, any local model | None (runs locally) |

Switch providers with a single env var — no code changes needed.

## Quick Start

### 1. Install

```bash
# Clone the repo
git clone https://github.com/manos02/gitlab-agent.git
cd gitlab-agent

# Create a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install
pip install -e .
```

### 2. Configure

```bash
cp .env.example .env
```

Edit `.env` with your settings:

```env
LLM_PROVIDER=google           # or: openai, anthropic, ollama
GOOGLE_API_KEY=...            # or OPENAI_API_KEY / ANTHROPIC_API_KEY
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-...        # GitLab personal access token
GITLAB_GROUP_ID=mygroup/platform  # optional default group path or ID (for cross-repo list/search)
OLLAMA_BASE_URL=http://localhost:11434/v1
```

**Getting a GitLab token:** Go to GitLab → Settings → Access Tokens → Create one with `api` scope.

### 3. Run The CLI

```bash
gitlab-agent
```

Then just type naturally:

```
You> Create a ticket called "Fix dark mode colors" with the bug label
  ⚙ create_issue(title='Fix dark mode colors', labels='bug')

Issue #47 created: Fix dark mode colors
URL: https://gitlab.com/yourproject/-/issues/47
```

### 4. Run The MCP Server

Use the packaged server entrypoint:

```bash
gitlab-agent-mcp
```

Or use the FastMCP CLI:

```bash
fastmcp run gitlab_agent/server.py:mcp
```

This defaults to `stdio`, which is the right transport for VS Code and Claude Code.

## MCP Clients

Use `gitlab-agent-mcp` as the server command in your MCP client configuration.

The server keeps session-scoped state for:

- Active GitLab group
- Active GitLab project

Use these tools first when needed:

- `set_active_group`
- `set_active_project`
- `clear_active_project`
- `get_active_scope`

### VS Code

Create [`.vscode/mcp.json`](/Users/manossavvides/programming/gitlab-agent/.vscode/mcp.json) in your workspace or open your user MCP configuration from the Command Palette with `MCP: Open User Configuration`.

Example workspace config:

```json
{
  "servers": {
    "gitlab-agent": {
      "type": "stdio",
      "command": "${workspaceFolder}/myenv/bin/gitlab-agent-mcp",
      "env": {
        "LLM_PROVIDER": "ollama",
        "LLM_MODEL": "qwen2.5",
        "OLLAMA_BASE_URL": "http://localhost:11434/v1",
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN": "${input:gitlab_token}",
        "GITLAB_GROUP_ID": "mygroup/platform"
      }
    }
  },
  "inputs": [
    {
      "id": "gitlab_token",
      "type": "promptString",
      "description": "GitLab personal access token"
    }
  ]
}
```

Then:

1. Run `MCP: List Servers` and start `gitlab-agent` if it is not already running.
2. Open Chat in agent mode.
3. Ask it to call `get_active_scope`, then `set_active_group` or `set_active_project`.
4. Use normal prompts such as `List all open issues` or `Create an issue called Fix login redirect`.

### Claude Code

Add the server as a local stdio MCP server:

```bash
claude mcp add --transport stdio --scope project gitlab-agent -- \
  /Users/manossavvides/programming/gitlab-agent/myenv/bin/gitlab-agent-mcp
```

If you want Claude Code to launch it with environment variables directly:

```bash
claude mcp add --transport stdio --scope project \
  --env LLM_PROVIDER=ollama \
  --env LLM_MODEL=qwen2.5 \
  --env OLLAMA_BASE_URL=http://localhost:11434/v1 \
  --env GITLAB_URL=https://gitlab.example.com \
  --env GITLAB_TOKEN=your-token \
  --env GITLAB_GROUP_ID=mygroup/platform \
  gitlab-agent -- /Users/manossavvides/programming/gitlab-agent/myenv/bin/gitlab-agent-mcp
```

Then inside Claude Code:

1. Run `/mcp` to confirm the server is connected.
2. Ask Claude to use `get_active_scope`.
3. Set scope with `set_active_group` or `set_active_project`.
4. Continue with normal requests.

Claude Code can also store this in [`.mcp.json`](/Users/manossavvides/programming/gitlab-agent/.mcp.json) at the project root when you use `--scope project`.

### Cursor

Cursor MCP support changes quickly, so use Cursor's MCP or Tools settings UI and register a local `stdio` server that runs:

```bash
/Users/manossavvides/programming/gitlab-agent/myenv/bin/gitlab-agent-mcp
```

Use the same environment variables you would use in VS Code or Claude Code:

- `LLM_PROVIDER`
- `LLM_MODEL`
- `OLLAMA_BASE_URL`
- `GITLAB_URL`
- `GITLAB_TOKEN`
- `GITLAB_GROUP_ID`

If Cursor offers JSON-based MCP configuration in your version, use a local stdio server with the same command and env values shown in the VS Code example above.

### First Use In Any MCP Client

Once the server is connected:

1. Call `get_active_scope`.
2. If needed, call `set_active_group` with your group path.
3. For create or update actions, call `set_active_project` with the full project path.
4. Then use prompts like `list open issues`, `show MR 42`, or `create a bug issue for login redirect`.

Important:

- The MCP server does not use the CLI chat loop.
- You should not type directly into `gitlab-agent-mcp` in a terminal.
- `gitlab-agent-mcp` is only for MCP clients to launch over `stdio`.

## CLI Commands

| Command                 | Description                         |
| ----------------------- | ----------------------------------- |
| `/help`                 | Show available commands             |
| `/reset`                | Clear conversation history          |
| `/group <id-or-path>`   | Set active group for this session   |
| `/project <id-or-path>` | Set active project for this session |
| `/clear-project`        | Clear active project scope          |
| `/quit`                 | Exit the agent                      |

Scope notes:

- `list_issues`, `list_merge_requests`, `search_project`, `list_milestones`, and boards prefer the active project and otherwise fall back to the active group where GitLab supports it.
- Create/update/close issue, labels, MR-by-IID operations, and issue-by-IID operations remain project-scoped.
- Scope now lives in the MCP session instead of custom CLI-only state.

## Architecture

```
gitlab_agent/
├── agent.py              # CLI chat agent (LLM ↔ FastMCP client)
├── cli.py                # Interactive CLI
├── config.py             # Environment-driven configuration
├── gitlab_client.py      # GitLab REST API wrapper
├── server.py             # FastMCP server and GitLab tools
└── llm/
  ├── base.py           # Abstract LLM provider interface
  ├── factory.py        # Provider instantiation
  ├── openai_provider.py
  ├── anthropic_provider.py
  └── google_provider.py
```

**Key design principles:**

- **FastMCP-first** — one MCP server is the source of truth for GitLab operations
- **Provider-agnostic CLI** — the chat client still works with OpenAI, Anthropic, Google, and Ollama-compatible local models
- **Shared tool surface** — VS Code, Claude Code, and the CLI all use the same MCP tools
- **Less framework code** — no custom tool registry or duplicated tool schema definitions

## Adding A New Tool

1. Add a Python function in `gitlab_agent/server.py`
2. Decorate it with `@mcp.tool`
3. Give it a clear signature and docstring

FastMCP generates the schema automatically, and both MCP clients and the CLI chat agent will see it.

## Adding A New LLM Provider

1. Create a class extending `BaseLLMProvider` in `gitlab_agent/llm/`
2. Implement `chat()` and `model_name`
3. Add it to the factory in `gitlab_agent/llm/factory.py`
4. Add the provider name to `DEFAULT_MODELS` in `config.py`

## License

MIT
