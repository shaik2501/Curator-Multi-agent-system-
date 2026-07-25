# 02 — Architecture & Tech Stack

## High-Level System

```
┌──────────────────────────────────────────────┐
│  Frontend — Next.js 14 (App Router)          │
│  Blue dashboard · SSE live feed · report view│
└──────────────────┬───────────────────────────┘
                   │ REST + Server-Sent Events
┌──────────────────▼───────────────────────────┐
│  Backend — FastAPI (Python 3.11+)            │
│  /runs  /runs/{id}/events  /runs/{id}/report │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  Orchestrator — LangGraph StateGraph         │
│  Supervisor → workers → memory → debate →    │
│  synthesis                                   │
└───────┬──────────────────────────┬───────────┘
        │                          │
┌───────▼────────┐        ┌────────▼──────────┐
│ LLM Provider   │        │ Storage           │
│ Claude API or  │        │ SQLite (runs) +   │
│ Ollama (local) │        │ ChromaDB (memory) │
└────────────────┘        └───────────────────┘
```

## Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration | **LangGraph** | Explicit graph control for supervisor/worker + debate loops |
| LLM #1 | **Claude API** (`claude-sonnet-5` workers, `claude-haiku-4-5` for cheap steps) | Quality research + long reports |
| LLM #2 | **Ollama** (`llama3.1:8b` or `qwen2.5:7b`) | Free, offline fallback |
| Provider switch | `init_chat_model` / small factory in `llm.py` | One env var or per-run flag swaps providers |
| Backend API | **FastAPI + uvicorn** | Async, easy SSE streaming |
| Web search tool | **Tavily API** (free tier) or DuckDuckGo (`ddgs`, no key) | Web Agent needs search |
| Shared memory | **ChromaDB** (embedded) | Vector knowledge base agents read/write |
| Run storage | **SQLite** via SQLModel | Zero-setup history |
| Frontend | **Next.js 14 + Tailwind CSS + shadcn/ui** | Fast to build the blue dashboard |
| Report render | `react-markdown` | Display final report |

## LangGraph Design

### State (single shared object)

```python
class ResearchState(TypedDict):
    goal: str
    plan: list[Subtask]          # created by Supervisor
    notes: list[Note]            # {agent, content, sources[]} → also embedded in ChromaDB
    draft: str                   # Writing Agent output
    critiques: list[Critique]    # Critic output, max 2 debate rounds
    report: str                  # final synthesis
    next_agent: str              # Supervisor routing decision
    provider: str                # "claude" | "ollama"
```

### Graph

```
START → supervisor
supervisor → (conditional edge on next_agent) → web_agent | data_agent | coding_agent | writing_agent
each worker → supervisor            # report back, Supervisor re-plans
supervisor → debate  (when draft exists and plan is complete)
debate: writer ↔ critic, max 2 rounds → synthesis
synthesis → END
```

Rules:
- Supervisor is the only router. Workers never call each other.
- Every worker writes findings to `notes` AND embeds them into ChromaDB.
- Writer/Synthesis query ChromaDB for relevant notes instead of stuffing everything into context.
- Hard caps: max 12 supervisor turns, max 2 debate rounds, per-run token budget → prevents infinite loops.

## Agents (system-prompt sketch)

- **supervisor**: "You manage a research team… Output JSON: {next_agent, task, reason} or {action: 'finish_research'}."
- **web_agent**: has `search_web(query)` and `fetch_page(url)` tools; must return facts with source URLs.
- **data_agent**: receives tables/numbers from notes; outputs comparisons, rankings, simple stats.
- **coding_agent**: has a sandboxed `run_python(code)` tool (subprocess, 10s timeout, no network).
- **writing_agent**: queries knowledge base, writes markdown sections with inline citations `[1]`.
- **critic**: attacks the draft — unsupported claims, missing perspectives, weak sources. Outputs a structured critique list.
- **synthesis**: merges draft + critiques + notes into the final report with a Sources section.

## API Contract

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/runs` | POST `{goal, provider}` | Start a run, returns `{run_id}` |
| `/api/runs/{id}/events` | GET (SSE) | Stream: `agent_started`, `agent_message`, `note_added`, `debate_turn`, `report_ready`, `error` |
| `/api/runs/{id}` | GET | Run status + report |
| `/api/runs` | GET | Run history |
| `/api/runs/{id}/knowledge` | GET | Knowledge base entries for the run |

## Repo Layout

```
research-crew/
├── CLAUDE.md
├── docs/                  # these planning docs
├── backend/
│   ├── app/main.py        # FastAPI app + SSE
│   ├── app/graph.py       # LangGraph build
│   ├── app/state.py       # ResearchState
│   ├── app/agents/        # supervisor.py, web.py, data.py, coding.py, writing.py, critic.py, synthesis.py
│   ├── app/tools/         # search.py, fetch.py, python_exec.py
│   ├── app/llm.py         # provider factory (claude | ollama)
│   ├── app/memory.py      # ChromaDB wrapper
│   ├── app/db.py          # SQLite models
│   └── pyproject.toml
└── frontend/
    ├── app/page.tsx           # dashboard: goal input + provider toggle
    ├── app/runs/[id]/page.tsx # live run view (feed, agents, debate, report)
    ├── components/            # AgentCard, ActivityFeed, DebatePanel, ReportView, KnowledgePanel
    └── tailwind.config.ts     # blue theme tokens (see 03-UI-DESIGN.md)
```
