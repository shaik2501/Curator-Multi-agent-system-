# 05 — Build Plan (Phased)

Each phase ends with something runnable. Feed phases to Claude Code one at a time. Estimated total: 5 focused sessions.

## Phase 0 — Scaffold (30 min)

- [ ] Create repo `research-crew/` with layout from 02-ARCHITECTURE.md
- [ ] Backend: FastAPI app with `GET /health`; pyproject with all deps
- [ ] Frontend: `npx create-next-app@14` + Tailwind + blue tokens from 04-UI-DESIGN.md
- [ ] `.env.example` for both sides

**Done when:** `uvicorn` serves /health, `npm run dev` shows a blue placeholder page.

## Phase 1 — LLM Layer + Single Agent (1 session)

- [ ] `app/llm.py`: `get_llm(provider, tier)` → ChatAnthropic or ChatOllama from env
- [ ] `app/tools/search.py`: Tavily with DuckDuckGo fallback; `app/tools/fetch.py`: httpx + BeautifulSoup text extraction
- [ ] Web Agent alone as a mini LangGraph: goal → search → fetch → summarize with sources
- [ ] CLI test script: `python -m app.test_web_agent "some topic"`

**Done when:** CLI prints a sourced summary using BOTH providers (switch via env var).

## Phase 2 — Full Graph (1–2 sessions)

- [ ] `app/state.py` ResearchState; `app/agents/*` all 7 agents
- [ ] `app/graph.py`: supervisor routing, worker→supervisor edges, debate loop (max 2 rounds), synthesis
- [ ] `app/memory.py`: ChromaDB add/query; workers write notes, Writer/Synthesis query
- [ ] `app/tools/python_exec.py`: sandboxed subprocess (10s timeout, no network)
- [ ] Turn caps + token budget guard
- [ ] CLI: `python -m app.run "goal"` prints final report

**Done when:** an end-to-end run produces a cited markdown report from the CLI.

## Phase 3 — API + Persistence (1 session)

- [ ] SQLite models: Run(id, goal, provider, status, report, created_at), Event, Note
- [ ] Endpoints from 02-ARCHITECTURE.md; graph emits events via an async queue → SSE
- [ ] Background task runs the graph; events persisted as they stream

**Done when:** `curl POST /api/runs` then `curl /api/runs/{id}/events` streams live events to completion.

## Phase 4 — Frontend (1–2 sessions)

- [ ] Dashboard page: goal input, provider toggle, team row, recent runs (per 04-UI-DESIGN.md)
- [ ] Live run page: 3-column layout — AgentPanel, ActivityFeed (SSE via EventSource), tabs (Knowledge/Plan/Report)
- [ ] DebateBubble styling (Writer blue / Critic amber), ReportView with react-markdown + download
- [ ] History page

**Done when:** full flow works in browser: type goal → watch agents live → read/download report.

## Phase 5 — Polish + Verify (1 session)

- [ ] Error states: provider unreachable, search failing, run stopped
- [ ] Motion polish per 04-UI-DESIGN.md; `prefers-reduced-motion`
- [ ] Backend tests: routing decision parsing, debate cap, budget guard, python_exec sandbox
- [ ] README with setup + screenshots
- [ ] Verification checklist below

## Final Verification Checklist

1. Run with Claude provider: report has ≥5 working source links
2. Run with Ollama provider offline: completes (quality may be lower)
3. Kill Ollama mid-run: UI shows a clean error, run marked failed
4. Debate never exceeds 2 rounds; supervisor never exceeds 12 turns
5. `python_exec` refuses network access and times out at 10s
6. Refresh the live run page mid-run: feed resumes from persisted events

## Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Supervisor loops forever | Hard turn cap → force synthesis |
| Ollama 8B outputs broken JSON routing | Structured-output retry ×3, then default route to Writer |
| Context overflow on long research | Notes live in ChromaDB; agents get top-k retrieval, not full history |
| Search rate limits | DuckDuckGo fallback + per-run search cap (15) |
