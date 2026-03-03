# GitLab Agent

An open-source AI agent that lets you manage your GitLab project through natural language.

## What can it do?

Talk to your GitLab project like you'd talk to a teammate:

- **"Create a bug ticket about the login page crashing"** → Creates an issue with the `bug` label
- **"Find the ticket about the search feature"** → Searches issues by keyword
- **"Create 3 tickets for X, Y, Z and put them in the Sprint column"** → Creates issues and moves them to the right board column
- **"What's the status of the MR for ticket #42?"** → Shows MR details, pipeline status, approvals
- **"List all open issues with the urgent label"** → Filters and lists issues
- **"Close issue #15"** → Closes the issue

## Supported LLM Providers

| Provider  | Models                      | Env Variable        |
| --------- | --------------------------- | ------------------- |
| Google    | Gemini 2.0 Flash, Pro, etc. | `GOOGLE_API_KEY`    |
| OpenAI    | GPT-4o, GPT-4, etc.         | `OPENAI_API_KEY`    |
| Anthropic | Claude Sonnet, Opus, etc.   | `ANTHROPIC_API_KEY` |
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
LLM_PROVIDER=google          # or: openai, anthropic
GOOGLE_API_KEY=...            # free at https://aistudio.google.com/apikey
GITLAB_URL=https://gitlab.com
GITLAB_TOKEN=glpat-...        # GitLab personal access token
GITLAB_GROUP_ID=mygroup/platform  # optional default group path or ID (for cross-repo list/search)
```

**Getting a GitLab token:** Go to GitLab → Settings → Access Tokens → Create one with `api` scope.

**Finding your project ID:** Go to your project page → it's shown under the project name, or in Settings → General.

### 3. Run

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

## CLI Commands

| Command  | Description                |
| -------- | -------------------------- |
| `/help`  | Show available commands    |
| `/reset` | Clear conversation history |
| `/project <id-or-path>` | Set active project for this session |
| `/group <id-or-path>` | Set active group for this session |
| `/quit`  | Exit the agent             |

Group scope notes:
- `list_issues`, `list_merge_requests`, `search_project`, and `list_milestones` work with either project or group scope.
- If no project is active, the agent prefers group endpoints where available.
- Create/update/close issue, labels, and MR-by-IID operations remain project-scoped.

Project alias notes:
- On startup, the agent fetches projects from `groups/:id/projects` (using `GITLAB_GROUP_ID`) and builds aliases in memory.
- Aliases include project name/path variants mapped to project IDs.
- When a user message includes one of these aliases, the agent auto-selects that project.

## Architecture

```
gitlab_agent/
├── agent.py              # Core agent loop (LLM ↔ tools)
├── cli.py                # CLI chat interface
├── config.py             # Configuration from env vars
├── gitlab_client.py      # GitLab REST API wrapper
├── llm/
│   ├── base.py           # Abstract LLM provider interface
│   ├── factory.py        # Provider instantiation
│   ├── openai_provider.py
│   ├── anthropic_provider.py
│   └── google_provider.py
└── tools/
    ├── base.py           # Tool interface + registry
    ├── registry.py       # Wires up all tools
    ├── issues.py         # Issue CRUD
    ├── labels.py         # Label management
    ├── merge_requests.py # MR info + pipelines
    ├── boards.py         # Board column management
    └── search.py         # Search + milestones
```

**Key design principles:**

- **Provider-agnostic** — LLM providers implement a common interface; swap with one env var
- **Tool-based** — each GitLab operation is a self-describing tool with a JSON schema
- **Decoupled UI** — the agent core has no knowledge of the CLI; a web UI can be added without touching the agent
- **Single agent** — one LLM conversation with tool access, simple and debuggable

## Adding a New Tool

1. Create a class extending `Tool` in the appropriate file under `gitlab_agent/tools/`
2. Implement `name`, `description`, `parameters` (JSON schema), and `run()`
3. Register it in `gitlab_agent/tools/registry.py`

That's it — the agent will automatically make it available to the LLM.

## Adding a New LLM Provider

1. Create a class extending `BaseLLMProvider` in `gitlab_agent/llm/`
2. Implement `chat()` and `model_name`
3. Add it to the factory in `gitlab_agent/llm/factory.py`
4. Add the provider name to `DEFAULT_MODELS` in `config.py`

## License

MIT
