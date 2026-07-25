# 04 — UI Design (Blue Theme)

Replaces the orange look from the reference material with a deep-blue, modern dashboard. See `ui-mockup.html` for a working visual preview.

## Design Language

Dark navy base, electric-blue accents, glassy cards, monospace only for the architecture/terminal panel. Clean, spacious, "mission control" feel.

## Color Tokens (Tailwind config)

```js
colors: {
  bg:        '#0A1120',  // page background (deep navy)
  surface:   '#101B33',  // cards
  surface2:  '#16233F',  // raised cards / hover
  border:    '#1F3358',  // card borders
  primary:   '#3B82F6',  // blue-500 — buttons, links, active agent
  primary2:  '#60A5FA',  // blue-400 — hovers, highlights
  accent:    '#38BDF8',  // sky-400 — live/streaming indicators
  ink:       '#E6EEFB',  // primary text
  inkMuted:  '#8FA3C7',  // secondary text
  success:   '#34D399',  // agent done
  warn:      '#FBBF24',  // critic flags
  danger:    '#F87171',  // errors
}
```

Gradients: hero/CTA `linear-gradient(135deg, #1D4ED8 → #38BDF8)`; card glow `0 0 24px rgba(59,130,246,.15)`.

## Typography

- UI: **Inter** (Google Fonts) — 600/700 headings, 400/500 body
- Code/architecture panel: **JetBrains Mono**
- Sizes: h1 28px, h2 20px, body 14px, feed 13px

## Screens

### 1. Dashboard (`/`)
- Top nav: logo "◇ Curator", links (Dashboard, History), provider badge
- Hero: big goal textarea with placeholder *"What should the team research?"*, blue gradient **Start Research** button
- Provider toggle: segmented control `Claude ⇄ Ollama (local)`
- Below: agent team row — 7 small cards (icon, name, one-line role), idle state
- Recent runs list (title, date, status chip)

### 2. Live Run (`/runs/[id]`) — main screen
Three-column layout:
- **Left — Agent Panel**: vertical list of agent cards. States: idle (dim), working (blue pulse ring + spinner), done (green check), flagged (amber). Shows current task under name.
- **Center — Activity Feed**: streaming timeline of events; each entry = agent avatar chip + timestamp + message. Debate turns render as chat bubbles: Writer (blue, left) vs Critic (amber, right). Auto-scroll with pause-on-hover.
- **Right — tabs**: `Knowledge Base` (note cards with source links) | `Plan` (subtask checklist) | `Report` (appears when ready).
- Top bar: goal text, elapsed time, provider badge, progress bar (subtasks done / total), Stop button.

### 3. Report view
Rendered markdown, sticky table of contents, Sources section, **Download .md** button, "Ask a follow-up" input (starts a new run seeded with the report).

### 4. History (`/history`)
Table: goal, date, provider, duration, status → click opens the run.

## Components

`AgentCard`, `ActivityFeed`, `FeedEvent`, `DebateBubble`, `KnowledgeCard`, `PlanChecklist`, `ReportView`, `ProviderToggle`, `RunProgressBar`, `StatusChip`

## Motion & Polish

- Working agent: soft blue pulse (`animate-pulse` ring, 2s)
- Feed events: fade+slide in (framer-motion, 150ms)
- Report ready: subtle confetti-free glow sweep on the Report tab
- Respect `prefers-reduced-motion`

## Accessibility

- Contrast ≥ 4.5:1 for text on `bg`/`surface` (tokens above pass)
- All live regions use `aria-live="polite"`
- Keyboard: goal textarea ⌘/Ctrl+Enter submits
