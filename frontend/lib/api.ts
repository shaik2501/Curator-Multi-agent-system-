// Fetch helpers + SSE subscription helper for the Curator backend.
// The backend is developed in parallel, so every call here is defensive:
// non-2xx / non-JSON / missing-field responses are normalized rather than
// thrown as raw exceptions where reasonably possible.

import type {
  AgentKey,
  CreateLLMConfigPayload,
  KnowledgeEntry,
  ListModelsPayload,
  ListModelsResponse,
  LLMConfig,
  RunDetail,
  RunEvent,
  RunEventType,
  RunSummary,
  SettingsResponse,
} from "./types";

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status?: number;
  constructor(message: string, status?: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_BASE_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init?.headers || {}),
      },
      cache: "no-store",
    });
  } catch {
    throw new ApiError(
      `Could not reach the backend at ${API_BASE_URL}. Is it running?`,
    );
  }

  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.detail || body?.message || "";
    } catch {
      // ignore non-JSON error bodies
    }
    throw new ApiError(
      detail || `Request failed with status ${res.status}`,
      res.status,
    );
  }

  try {
    return (await res.json()) as T;
  } catch {
    // Some endpoints (e.g. a stop action) may return no body.
    return {} as T;
  }
}

/**
 * POST /api/runs -> { run_id }. Body carries a per-agent-role LLM config
 * assignment (all 7 AGENT_KEYS required) — the old flat `provider_config_id`
 * field is gone from the API contract.
 */
export async function createRun(
  goal: string,
  agentConfigs: Record<AgentKey, string>,
): Promise<{ run_id: string }> {
  const data = await request<{ run_id?: string; id?: string }>("/api/runs", {
    method: "POST",
    body: JSON.stringify({ goal, agent_configs: agentConfigs }),
  });
  const run_id = data.run_id || data.id;
  if (!run_id) {
    throw new ApiError("Backend did not return a run_id.");
  }
  return { run_id };
}

/** GET /api/runs -> run history list (defaults to []) */
export async function listRuns(): Promise<RunSummary[]> {
  const data = await request<RunSummary[] | { runs?: RunSummary[] }>(
    "/api/runs",
  );
  if (Array.isArray(data)) return data;
  return data.runs ?? [];
}

/** GET /api/runs/{id} -> run status + report */
export async function getRun(id: string): Promise<RunDetail> {
  return request<RunDetail>(`/api/runs/${id}`);
}

/** GET /api/runs/{id}/knowledge -> knowledge base entries (defaults to []) */
export async function getKnowledge(id: string): Promise<KnowledgeEntry[]> {
  const data = await request<
    KnowledgeEntry[] | { entries?: KnowledgeEntry[]; notes?: KnowledgeEntry[] }
  >(`/api/runs/${id}/knowledge`);
  if (Array.isArray(data)) return data;
  return data.entries ?? data.notes ?? [];
}

/**
 * POST /api/runs/{id}/stop — real cancellation. Callers should surface a
 * failure to the user (don't swallow it): if this rejects, the run was NOT
 * actually stopped server-side even though the UI may show it as such.
 */
export async function stopRun(id: string): Promise<{ ok: true } | { ok: false; message: string }> {
  try {
    await request(`/api/runs/${id}/stop`, { method: "POST" });
    return { ok: true };
  } catch (err) {
    return {
      ok: false,
      message:
        err instanceof ApiError
          ? err.message
          : "Could not reach the backend to stop this run.",
    };
  }
}

/**
 * GET /api/settings — system-level config/status (no per-user accounts in
 * v1). May not be deployed yet; callers should treat a thrown ApiError with
 * status 404 as "backend not updated yet" rather than a hard failure.
 */
export async function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings");
}

/** GET /health — liveness ping used by the topbar status popover. */
export async function getHealth(): Promise<{ status?: string }> {
  return request<{ status?: string }>("/health");
}

/**
 * POST /api/providers/ollama/check — on-demand, uncached live connectivity
 * check (distinct from the possibly-stale `reachable` field in
 * /api/settings). May not be deployed yet; callers should handle rejection.
 */
export async function checkOllama(): Promise<{ reachable: boolean }> {
  return request<{ reachable: boolean }>("/api/providers/ollama/check", {
    method: "POST",
  });
}

/** GET /api/llm-configs -> the user's saved LLM configs (defaults to []). */
export async function listLLMConfigs(): Promise<LLMConfig[]> {
  const data = await request<LLMConfig[] | { configs?: LLMConfig[] }>(
    "/api/llm-configs",
  );
  if (Array.isArray(data)) return data;
  return data.configs ?? [];
}

/**
 * POST /api/llm-configs — creates a config and live-verifies it immediately;
 * the returned config's `status`/`last_error` reflect that verification.
 */
export async function createLLMConfig(
  payload: CreateLLMConfigPayload,
): Promise<LLMConfig> {
  return request<LLMConfig>("/api/llm-configs", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/** POST /api/llm-configs/{id}/verify — re-checks a saved config on demand. */
export async function verifyLLMConfig(id: string): Promise<LLMConfig> {
  return request<LLMConfig>(`/api/llm-configs/${id}/verify`, {
    method: "POST",
  });
}

/** DELETE /api/llm-configs/{id}. */
export async function deleteLLMConfig(id: string): Promise<void> {
  await request(`/api/llm-configs/${id}`, { method: "DELETE" });
}

/**
 * POST /api/llm-configs/list-models — stateless live model lookup, nothing
 * is saved. Always 200 on the backend's side; a non-null `error` with an
 * empty list is a normal outcome (bad key, endpoint doesn't support
 * listing), not something callers should treat as a thrown exception.
 */
export async function listModels(payload: ListModelsPayload): Promise<ListModelsResponse> {
  return request<ListModelsResponse>("/api/llm-configs/list-models", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type RunEventHandler = (event: RunEvent) => void;

export interface SubscribeOptions {
  onEvent: RunEventHandler;
  onError?: (err: Event) => void;
  onOpen?: () => void;
  /** Explicit event type names to listen for, in addition to the default message handler. */
  eventTypes?: RunEventType[];
}

const DEFAULT_EVENT_TYPES: RunEventType[] = [
  "agent_started",
  "agent_message",
  "note_added",
  "debate_turn",
  "report_ready",
  "error",
];

/**
 * Subscribes to GET /api/runs/{id}/events via EventSource.
 * Parses event.data as JSON defensively; malformed payloads are wrapped
 * rather than dropped so the UI can still surface something went wrong.
 * Returns an unsubscribe function that closes the connection.
 */
export function subscribeToRunEvents(
  runId: string,
  { onEvent, onError, onOpen, eventTypes }: SubscribeOptions,
): () => void {
  const url = `${API_BASE_URL}/api/runs/${runId}/events`;
  const source = new EventSource(url);

  function parseAndEmit(type: RunEventType, raw: MessageEvent) {
    let data: unknown = raw.data;
    if (typeof raw.data === "string") {
      try {
        data = JSON.parse(raw.data);
      } catch {
        data = { message: raw.data };
      }
    }
    onEvent({ type, data, id: raw.lastEventId || undefined });
  }

  // Named SSE events (event: agent_started\ndata: {...}).
  // NOTE: "error" is a reserved EventSource event name. The browser fires a
  // plain `Event` (no `.data`) on connection failures via the SAME "error"
  // listener that we also use for the backend's named `error` domain event
  // (a real `MessageEvent` with JSON `.data`). We must tell them apart here
  // and never forward the connection-failure Event as if it were a domain
  // error payload, or downstream code will crash reading `.message` off
  // `undefined`.
  const types = eventTypes ?? DEFAULT_EVENT_TYPES;
  const listeners: Array<[string, (e: Event) => void]> = [];
  for (const t of types) {
    const handler = (e: Event) => {
      if (t === "error" && !(e instanceof MessageEvent)) {
        // Native connection-error Event, not a backend `error` domain event.
        onError?.(e);
        return;
      }
      parseAndEmit(t, e as MessageEvent);
    };
    source.addEventListener(t, handler);
    listeners.push([t, handler]);
  }

  // Fallback: default "message" event, in case the backend doesn't set
  // named event types and instead sends a `type` field inside the payload.
  source.onmessage = (e: MessageEvent) => {
    let data: unknown;
    try {
      data = JSON.parse(e.data);
    } catch {
      data = { message: e.data };
    }
    const inferredType =
      (data as { type?: RunEventType })?.type ?? "agent_message";
    onEvent({ type: inferredType, data, id: e.lastEventId || undefined });
  };

  if (onOpen) source.onopen = () => onOpen();
  // Do NOT also set source.onerror here: when "error" is included in `types`
  // (the default), our addEventListener("error", ...) handler above already
  // covers both native connection failures and named error events. Setting
  // both would double-fire onError for the same connection failure.
  if (onError && !types.includes("error")) {
    source.onerror = (e) => onError(e);
  }

  return () => {
    for (const [t, handler] of listeners) {
      source.removeEventListener(t, handler);
    }
    source.close();
  };
}
