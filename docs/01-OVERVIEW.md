# 01 — Project Overview

## What We Are Building

**Curator** — a Multi-Agent Research Team application. A user types a research goal (e.g., *"Compare the top 3 vector databases for a startup"*), and a team of specialized AI agents collaborates like a company team to produce a polished, cited research report.

## The Agent Team

| Agent | Role |
|---|---|
| **Supervisor (Planner)** | Breaks the goal into subtasks, delegates to workers, decides when work is done |
| **Web Research Agent** | Searches the web, fetches pages, extracts facts with sources |
| **Data Agent** | Analyzes numbers/tables found during research, produces comparisons and stats |
| **Coding Agent** | Writes/runs small code snippets when the task needs computation or examples |
| **Writing Agent** | Drafts report sections from the shared research notes |
| **Critic Agent** | Challenges drafts — flags weak evidence, missing angles, contradictions |
| **Reviewer/Synthesis Agent** | Resolves the debate, merges everything into the final report |

## Architecture Flow (from the original design)

```
User Research Goal
        ↓
  Supervisor Agent
        ↓
Task Distribution Layer
   ↓      ↓      ↓       ↓
 Web    Data  Coding  Writing
 Agent  Agent  Agent   Agent
   ↓      ↓      ↓       ↓
 Shared Memory / Knowledge Base
        ↓
 Reasoning & Debate Layer  (Writer ↔ Critic)
        ↓
 Report Synthesis Agent
        ↓
 Final Research Report
```

## Skills This Project Teaches

- Agent orchestration (supervisor/worker pattern)
- Task delegation and routing
- Long-term / shared memory between agents
- Multi-agent systems and agent debate
- Full-stack integration (Python agent backend + Next.js frontend)

## Core Features (v1)

1. Submit a research goal from a blue-themed web dashboard
2. Live activity feed — watch each agent work in real time (streaming)
3. Shared knowledge base viewer — see what agents have learned
4. Debate view — Writer vs Critic exchanges
5. Final report rendered as markdown, downloadable as .md
6. Run history — past research runs stored in SQLite
7. LLM provider toggle: **Claude API** or **local Ollama** (per run)

## Out of Scope (v1)

PDF export, user accounts/auth, multi-user collaboration, agent fine-tuning, paid deployment. Add later if wanted.

## Success Criteria

- A research goal completes end-to-end in under ~5 minutes (Claude API)
- Report contains ≥5 cited sources with working URLs
- Works fully offline with Ollama (slower, lower quality is acceptable)
- UI streams agent activity with <2s latency per event
