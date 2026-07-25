# 03 — Requirements & Setup

## What You Need Before Building

### Accounts / API Keys

| Item | Required? | Cost | Where |
|---|---|---|---|
| Anthropic API key | Yes (for Claude provider) | Pay-per-use (~$1–3 per full run on Sonnet) | console.anthropic.com |
| Tavily API key | Optional (better search) | Free tier: 1,000 searches/mo | tavily.com |
| Ollama | Yes (for local provider) | Free | ollama.com |

No key at all? The app still works: Ollama provider + DuckDuckGo search.

### Software

- Python 3.11+
- Node.js 20+ and npm
- Git
- Ollama installed, then: `ollama pull llama3.1:8b` (needs ~8GB RAM; use `qwen2.5:7b` as alternative)

### Python dependencies (backend/pyproject.toml)

```
langgraph, langchain, langchain-anthropic, langchain-ollama,
fastapi, uvicorn[standard], sse-starlette,
chromadb, sqlmodel,
tavily-python, ddgs, httpx, beautifulsoup4,
pydantic, python-dotenv
```

### Frontend dependencies

```
next@14, react, tailwindcss, shadcn/ui,
react-markdown, lucide-react, framer-motion (subtle animations)
```

## Environment Variables (backend/.env)

```env
ANTHROPIC_API_KEY=sk-ant-...        # required for provider=claude
TAVILY_API_KEY=tvly-...             # optional; falls back to DuckDuckGo
DEFAULT_PROVIDER=claude             # claude | ollama
CLAUDE_MODEL=claude-sonnet-5
CLAUDE_CHEAP_MODEL=claude-haiku-4-5
OLLAMA_MODEL=llama3.1:8b
OLLAMA_BASE_URL=http://localhost:11434
DB_PATH=./data/runs.db
CHROMA_PATH=./data/chroma
MAX_SUPERVISOR_TURNS=12
MAX_DEBATE_ROUNDS=2
```

Frontend (.env.local): `NEXT_PUBLIC_API_URL=http://localhost:8000`

## Ports

- Backend: **8000**
- Frontend: **3000**
- Ollama: **11434**

## Run Commands

```bash
# backend
cd backend && pip install -e . && uvicorn app.main:app --reload --port 8000

# frontend
cd frontend && npm install && npm run dev

# ollama (separate terminal, only for local provider)
ollama serve
```

## Constraints & Safety

- Coding Agent executes Python in a subprocess: 10s timeout, no network, temp dir only.
- Web fetches: 15s timeout, max 100KB text extracted per page, respect robots meta.
- Per-run budget guard: stop and synthesize with whatever exists if token/turn caps are hit.
- Never commit `.env`; ship `.env.example`.
