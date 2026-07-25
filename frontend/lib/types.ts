// Shared TS types for the Curator frontend.
// Coded defensively: the backend is being built in parallel, so treat
// most fields as optional/unknown-tolerant and default arrays to [].

export type Provider = "claude" | "openai" | "gemini" | "ollama" | "custom";

export interface ProviderMeta {
  key: Provider;
  label: string;
  icon: string;
  description: string;
}

export const PROVIDER_META: Record<Provider, ProviderMeta> = {
  claude: {
    key: "claude",
    label: "Claude",
    icon: "bolt",
    description: "Anthropic's Claude models via the Claude API.",
  },
  openai: {
    key: "openai",
    label: "OpenAI",
    icon: "psychology",
    description: "OpenAI's GPT models (ChatGPT) via the OpenAI API.",
  },
  gemini: {
    key: "gemini",
    label: "Gemini",
    icon: "auto_awesome",
    description: "Google's Gemini models via the Gemini API.",
  },
  ollama: {
    key: "ollama",
    label: "Ollama (Local)",
    icon: "terminal",
    description: "Free, offline models running locally via Ollama.",
  },
  custom: {
    key: "custom",
    label: "Custom",
    icon: "tune",
    description: "Any OpenAI-compatible endpoint (OpenRouter, Groq, Together, LM Studio, vLLM, etc).",
  },
};

export const PROVIDER_KEYS: Provider[] = ["claude", "openai", "gemini", "ollama", "custom"];

/**
 * Example model names used ONLY as free-text input placeholder text in the
 * Add-LLM form (never silently prefilled/submitted as a value) — actual
 * model choices come from the live POST /api/llm-configs/list-models fetch.
 * Model names drift (e.g. gemini-1.5-* was deprecated), so nothing here is
 * trusted as a real default.
 */
export const PROVIDER_MODEL_PLACEHOLDER: Record<Provider, string> = {
  claude: "e.g. claude-opus-4-6",
  openai: "e.g. gpt-4o",
  gemini: "e.g. gemini-2.5-pro",
  ollama: "e.g. llama3.1:8b",
  custom: "model id",
};

export const PROVIDER_CHEAP_MODEL_PLACEHOLDER: Record<Provider, string> = {
  claude: "e.g. claude-haiku-4-5",
  openai: "e.g. gpt-4o-mini",
  gemini: "e.g. gemini-2.5-flash",
  ollama: "e.g. llama3.1:8b",
  custom: "model id",
};

/** Run status values we know about; backend may send others we haven't seen. */
export type RunStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "stopped"
  | (string & {});

export interface Subtask {
  id?: string;
  title?: string;
  description?: string;
  assigned_to?: string;
  done?: boolean;
  status?: string;
}

export interface NoteSource {
  url?: string;
  title?: string;
}

export interface Note {
  id?: string;
  agent?: string;
  content?: string;
  sources?: NoteSource[] | string[];
  created_at?: string;
}

export interface Critique {
  id?: string;
  agent?: string;
  content?: string;
  round?: number;
  created_at?: string;
}

/** Per-role LLM assignment snapshotted at run creation — survives later config deletion. */
export interface AgentModelSnapshot {
  config_id: string;
  provider_type: Provider | string;
  label?: string | null;
}

export interface RunSummary {
  id: string;
  goal: string;
  /**
   * Per-agent-role LLM assignment — the old flat `provider_config_id` /
   * `provider_type` / `provider_label` fields are gone.
   */
  agent_model_snapshot?: Partial<Record<AgentKey, AgentModelSnapshot>>;
  status?: RunStatus;
  created_at?: string;
  updated_at?: string;
  duration_seconds?: number;
}

export interface RunDetail extends RunSummary {
  report?: string | null;
  plan?: Subtask[];
  notes?: Note[];
  critiques?: Critique[];
  error?: string | null;
}

export interface KnowledgeEntry {
  id?: string;
  agent?: string;
  content?: string;
  sources?: NoteSource[] | string[];
  created_at?: string;
  score?: number;
  /** Present for the image agent's notes — a path served by GET /api/images/{run_id}/{filename}. */
  image_url?: string;
}

/** Known SSE event types from /api/runs/{id}/events. Unknown types are passed through. */
export type RunEventType =
  | "agent_started"
  | "agent_message"
  | "note_added"
  | "debate_turn"
  | "report_ready"
  | "error"
  | (string & {});

export interface RunEvent<T = unknown> {
  type: RunEventType;
  data: T;
  /** Raw event id from EventSource, if any. */
  id?: string;
}

export interface AgentStartedData {
  agent?: string;
  task?: string;
  turn?: number;
  round?: number;
}

export interface AgentMessageData {
  agent?: string;
  message?: string;
  content?: string;
}

/** Real backend shape: flat, not nested under `note`. */
export interface NoteAddedData {
  agent?: string;
  content?: string;
  sources?: NoteSource[] | string[];
  /** Present for the image agent's notes — a path served by GET /api/images/{run_id}/{filename}. */
  image_url?: string;
}

export interface DebateTurnData {
  agent?: string; // "writer" | "critic"
  role?: string;
  round?: number;
  message?: string;
  issues?: string[] | string;
  summary?: string;
  /** legacy/alternate field some payloads may use */
  content?: string;
}

export interface ReportReadyData {
  report?: string;
}

/** Real backend shape for the SSE `error` event's data. */
export interface ErrorEventData {
  message?: string;
  traceback?: string;
  /** legacy/alternate field some payloads may use */
  detail?: string;
}

export const AGENT_KEYS = [
  "supervisor",
  "web",
  "data",
  "coding",
  "writing",
  "critic",
  "synthesis",
  "image",
] as const;

export type AgentKey = (typeof AGENT_KEYS)[number];

export interface AgentMeta {
  key: AgentKey;
  name: string;
  role: string;
  /** Role accent color (hex) — left-border / icon / status-dot per the DS. */
  color: string;
  /** Material Symbols Outlined icon name. */
  icon: string;
  /** Short uppercase category badge shown on the dashboard crew cards. */
  category: string;
}

export const AGENT_TEAM: AgentMeta[] = [
  {
    key: "supervisor",
    name: "Supervisor",
    role: "Plans and delegates the research",
    color: "#8b5cf6",
    icon: "smart_toy",
    category: "System",
  },
  {
    key: "web",
    name: "Web Research",
    role: "Searches the web for facts and sources",
    color: "#38bdf8",
    icon: "travel_explore",
    category: "Research",
  },
  {
    key: "data",
    name: "Data",
    role: "Analyzes numbers, tables, comparisons",
    color: "#2dd4bf",
    icon: "monitoring",
    category: "Analysis",
  },
  {
    key: "image",
    name: "Image",
    role: "Generates images for the report.",
    color: "#ec4899",
    icon: "image",
    category: "Visual",
  },
  {
    key: "coding",
    name: "Coding",
    role: "Runs small scripts for computation",
    color: "#fbbf24",
    icon: "code",
    category: "Compute",
  },
  {
    key: "writing",
    name: "Writing",
    role: "Drafts report sections from notes",
    color: "#f472b6",
    icon: "edit_note",
    category: "Content",
  },
  {
    key: "critic",
    name: "Critic",
    role: "Challenges the draft for weaknesses",
    color: "#fb923c",
    icon: "gavel",
    category: "Logic",
  },
  {
    key: "synthesis",
    name: "Synthesis",
    role: "Merges everything into the final report",
    color: "#6366f1",
    icon: "auto_awesome",
    category: "Output",
  },
];

export type AgentState = "idle" | "working" | "done" | "flagged";

/**
 * GET /api/settings — simplified to just run-limit fields. Per-provider
 * config/status now lives in the LLMConfig list (/api/llm-configs), not here.
 */
export interface SettingsResponse {
  max_supervisor_turns?: number;
  max_debate_rounds?: number;
  max_searches_per_run?: number;
}

export type LLMConfigStatus = "verified" | "failed" | "unverified";

/** A user-saved, live-verified LLM credential/endpoint — /api/llm-configs*. */
export interface LLMConfig {
  id: string;
  label?: string | null;
  provider_type: Provider | string;
  /** Masked key preview (e.g. "sk-p...W9kA"); null for providers with no key (ollama). */
  key_preview?: string | null;
  base_url?: string | null;
  model: string;
  cheap_model?: string | null;
  status: LLMConfigStatus | string;
  last_checked_at?: string | null;
  last_error?: string | null;
  created_at?: string;
  /**
   * true for openai/gemini, false for claude/ollama, user-set at creation
   * for custom endpoints. Gates whether this config can be assigned to the
   * "image" agent role — the backend 400s on POST /api/runs otherwise.
   */
  image_capable?: boolean;
}

/** POST /api/llm-configs body. */
export interface CreateLLMConfigPayload {
  label?: string;
  provider_type: Provider;
  api_key?: string;
  base_url?: string;
  model: string;
  cheap_model?: string;
  /** Only meaningful (and user-editable) for provider_type "custom". */
  image_capable?: boolean;
}

/** POST /api/llm-configs/list-models body — stateless, nothing is saved. */
export interface ListModelsPayload {
  provider_type: Provider;
  api_key?: string;
  base_url?: string;
}

/**
 * POST /api/llm-configs/list-models response. Always 200; an empty `models`
 * list with a non-null `error` is a normal outcome (bad key, endpoint
 * doesn't support listing), not an exception path.
 */
export interface ListModelsResponse {
  models: string[];
  error: string | null;
}
