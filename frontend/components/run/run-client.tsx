"use client";

import { useEffect, useMemo, useRef, useState, useCallback } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { Tabs } from "@/components/ui/tabs";
import { AgentCard } from "@/components/agent-card";
import { NotificationsPanel } from "@/components/notifications/notifications-panel";
import { AgentKanbanBoard, type KanbanCard } from "@/components/run/agent-kanban-board";
import { KnowledgeCard } from "@/components/knowledge-card";
import { PlanChecklist } from "@/components/plan-checklist";
import { ReportView } from "@/components/report-view";
import { AgentModelSummary } from "@/components/agent-model-summary";
import {
  ApiError,
  getKnowledge,
  getRun,
  stopRun,
  subscribeToRunEvents,
} from "@/lib/api";
import { AGENT_TEAM } from "@/lib/types";
import type {
  AgentKey,
  AgentMessageData,
  AgentStartedData,
  AgentState,
  DebateTurnData,
  ErrorEventData,
  KnowledgeEntry,
  NoteAddedData,
  RunDetail,
  RunEvent,
  Subtask,
} from "@/lib/types";
import { formatElapsed, parseTimestampMs } from "@/lib/utils";

function toAgentKey(agent?: string): AgentKey {
  const lower = (agent || "").toLowerCase();
  const found = AGENT_TEAM.find(
    (a) => a.key === lower || a.name.toLowerCase() === lower,
  );
  return found?.key ?? "supervisor";
}

let idCounter = 0;
function nextId(prefix: string) {
  idCounter += 1;
  return `${prefix}-${idCounter}-${Date.now()}`;
}

export default function RunClient({ runId }: { runId: string }) {
  const [run, setRun] = useState<RunDetail | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);

  const [cardsByAgent, setCardsByAgent] = useState<Record<AgentKey, KanbanCard[]>>({
    supervisor: [],
    web: [],
    data: [],
    image: [],
    coding: [],
    writing: [],
    critic: [],
    synthesis: [],
  });
  const [sseErrors, setSseErrors] = useState<{ id: string; message: string }[]>([]);
  const pendingTurnRef = useRef<Partial<Record<AgentKey, number | undefined>>>({});
  const pendingTaskRef = useRef<Partial<Record<AgentKey, string | undefined>>>({});
  const [agentStates, setAgentStates] = useState<Record<AgentKey, AgentState>>(
    {
      supervisor: "idle",
      web: "idle",
      data: "idle",
      image: "idle",
      coding: "idle",
      writing: "idle",
      critic: "idle",
      synthesis: "idle",
    },
  );
  const [agentTasks, setAgentTasks] = useState<Partial<Record<AgentKey, string>>>(
    {},
  );
  const [plan, setPlan] = useState<Subtask[]>([]);
  const [knowledge, setKnowledge] = useState<KnowledgeEntry[]>([]);
  const [report, setReport] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState("knowledge");
  const [reportJustArrived, setReportJustArrived] = useState(false);
  const [stopped, setStopped] = useState(false);
  const [stopError, setStopError] = useState<string | null>(null);
  const [elapsed, setElapsed] = useState(0);

  const startTimeRef = useRef<number>(Date.now());
  const unsubscribeRef = useRef<(() => void) | null>(null);
  const seenEventIdsRef = useRef<Set<string>>(new Set());
  const terminalCloseTimerRef = useRef<ReturnType<typeof setTimeout> | null>(
    null,
  );

  const status = stopped ? "stopped" : run?.status ?? "running";
  const isTerminal = ["completed", "failed", "stopped"].includes(
    status.toString(),
  );
  const isTerminalRef = useRef(isTerminal);
  useEffect(() => {
    isTerminalRef.current = isTerminal;
  }, [isTerminal]);

  const closeStream = useCallback(() => {
    unsubscribeRef.current?.();
    unsubscribeRef.current = null;
    if (terminalCloseTimerRef.current) {
      clearTimeout(terminalCloseTimerRef.current);
      terminalCloseTimerRef.current = null;
    }
  }, []);

  // Initial load
  useEffect(() => {
    let cancelled = false;
    getRun(runId)
      .then((data) => {
        if (cancelled) return;
        setRun(data);
        setPlan(data.plan ?? []);
        if (data.report) setReport(data.report);
        const t = parseTimestampMs(data.created_at);
        if (t != null) startTimeRef.current = t;
        // Already-terminal run: the backend replays its persisted events once
        // on connect; give that a moment, then stop reconnect attempts.
        if (
          data.status &&
          ["completed", "failed", "stopped"].includes(data.status.toString())
        ) {
          terminalCloseTimerRef.current = setTimeout(closeStream, 2000);
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setLoadError(
            err instanceof ApiError
              ? err.message
              : "Could not load this run. Is the backend running?",
          );
        }
      });
    getKnowledge(runId)
      .then((data) => {
        if (!cancelled) setKnowledge(data);
      })
      .catch(() => {
        // non-fatal; knowledge tab will just show empty
      });
    return () => {
      cancelled = true;
    };
  }, [runId, closeStream]);

  // Elapsed timer — freeze against updated_at - created_at once the run is
  // terminal, instead of continuing to tick against "now".
  useEffect(() => {
    if (isTerminal) {
      const startMs = parseTimestampMs(run?.created_at) ?? startTimeRef.current;
      const endMs = parseTimestampMs(run?.updated_at) ?? Date.now();
      setElapsed(Math.max(0, (endMs - startMs) / 1000));
      return;
    }
    const interval = setInterval(() => {
      setElapsed((Date.now() - startTimeRef.current) / 1000);
    }, 1000);
    return () => clearInterval(interval);
  }, [isTerminal, run?.created_at, run?.updated_at]);

  // SSE subscription
  useEffect(() => {
    if (loadError) return;
    const unsubscribe = subscribeToRunEvents(runId, {
      onOpen: () => setConnected(true),
      onError: () => {
        setConnected(false);
        // A finished run intentionally has its stream closed (see below) or
        // was never expected to stay connected — don't alarm the user.
        if (!isTerminalRef.current) {
          setStreamError(
            "Lost connection to the live event stream. The run may still be progressing on the server.",
          );
        }
      },
      onEvent: (event: RunEvent) => {
        // Dedupe replayed events (EventSource reconnects replay persisted
        // events from the backend) using the stable SSE id when present.
        if (event.id) {
          if (seenEventIdsRef.current.has(event.id)) return;
          seenEventIdsRef.current.add(event.id);
        }
        handleEvent(event);
      },
    });
    unsubscribeRef.current = unsubscribe;
    return () => {
      unsubscribe();
      unsubscribeRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [runId, loadError]);

  const setAgentState = useCallback((agent: string | undefined, state: AgentState) => {
    const key = toAgentKey(agent);
    setAgentStates((prev) => ({ ...prev, [key]: state }));
  }, []);

  const addCard = useCallback((agent: AgentKey, card: KanbanCard) => {
    setCardsByAgent((prev) => ({ ...prev, [agent]: [...prev[agent], card] }));
  }, []);

  // NOTE: dedupe (seenEventIdsRef, in the SSE subscription effect above) and
  // close-on-terminal (the unsubscribeRef.current?.() calls below) are
  // unchanged from before — this rewrite only regroups the same event
  // stream into per-agent Kanban cards instead of one linear feed.
  const handleEvent = useCallback((event: RunEvent) => {
    switch (event.type) {
      case "agent_started": {
        const data = event.data as AgentStartedData | undefined;
        const key = toAgentKey(data?.agent);
        setAgentState(data?.agent, "working");
        if (data?.agent) {
          setAgentTasks((prev) => ({ ...prev, [key]: data.task ?? "" }));
        }
        if (key === "supervisor") {
          pendingTurnRef.current.supervisor = data?.turn;
        } else {
          pendingTaskRef.current[key] = data?.task;
        }
        break;
      }
      case "agent_message": {
        const data = event.data as AgentMessageData | undefined;
        const key = toAgentKey(data?.agent);
        const message = data?.message || data?.content || "";
        if (!message) break;
        if (key === "supervisor") {
          const turn = pendingTurnRef.current.supervisor;
          addCard("supervisor", {
            id: nextId("turn"),
            kind: "supervisor_turn",
            title: turn != null ? `Turn ${turn}` : "Routing decision",
            body: message,
            timestamp: new Date().toISOString(),
          });
        } else {
          // Lightweight status message (e.g. "Task complete; returning to
          // supervisor.") — still surfaced as its own small card so nothing
          // from the stream is lost in this column.
          addCard(key, {
            id: nextId("note"),
            kind: "note",
            title: "Update",
            body: message,
            timestamp: new Date().toISOString(),
          });
        }
        break;
      }
      case "note_added": {
        // Real backend shape is flat: {agent, content, sources[]}.
        const data = event.data as NoteAddedData | undefined;
        const key = toAgentKey(data?.agent);
        setAgentState(data?.agent, "done");
        if (data?.content || data?.image_url) {
          setKnowledge((prev) => [
            {
              agent: data.agent,
              content: data.content,
              sources: data.sources,
              image_url: data.image_url,
              created_at: new Date().toISOString(),
            },
            ...prev,
          ]);
        }
        const task = pendingTaskRef.current[key];
        addCard(key, {
          id: nextId("res"),
          kind: "task_result",
          title: task ? "Task" : "Result",
          subtitle: task,
          body: data?.content || (data?.image_url ? undefined : "(no content)"),
          imageUrl: data?.image_url,
          timestamp: new Date().toISOString(),
        });
        pendingTaskRef.current[key] = undefined;
        break;
      }
      case "debate_turn": {
        const data = event.data as DebateTurnData | undefined;
        const isCritic = (data?.role || data?.agent || "").toLowerCase() === "critic";
        const key: AgentKey = isCritic ? "critic" : "writing";
        setAgentState(key, "working");
        const issues = Array.isArray(data?.issues)
          ? data.issues.join("\n")
          : data?.issues;
        const content =
          data?.message || data?.content || data?.summary || issues || "";
        addCard(key, {
          id: nextId("dbt"),
          kind: isCritic ? "critic_turn" : "writer_revision",
          title:
            (isCritic ? "Critique" : "Revision") +
            (data?.round != null ? ` (round ${data.round})` : ""),
          body: content,
          timestamp: new Date().toISOString(),
        });
        break;
      }
      case "report_ready": {
        const data = event.data as { report?: string } | undefined;
        if (data?.report) setReport(data.report);
        setAgentState("synthesis", "done");
        setActiveTab("report");
        setReportJustArrived(true);
        setTimeout(() => setReportJustArrived(false), 3200);
        addCard("synthesis", {
          id: nextId("rpt"),
          kind: "report",
          title: "Final report ready",
          body: data?.report ? `${data.report.slice(0, 180)}…` : undefined,
          timestamp: new Date().toISOString(),
        });
        // report_ready means the run reached a terminal state — stop
        // reconnecting so we don't keep replaying old events.
        unsubscribeRef.current?.();
        unsubscribeRef.current = null;
        break;
      }
      case "error": {
        const data = event.data as ErrorEventData | undefined;
        const message = data?.message || data?.detail || "An error occurred.";
        setSseErrors((prev) => [...prev, { id: nextId("sseerr"), message }]);
        // A run's error event signals a terminal (failed) run — the backend
        // will keep replaying this single event on every reconnect, so stop.
        unsubscribeRef.current?.();
        unsubscribeRef.current = null;
        break;
      }
      default: {
        // Unknown event type: no dedicated column mapping, so drop it rather
        // than guess which agent it belongs to (nothing to lose visibility
        // of — every known event type above already has a home).
        break;
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleStop = async () => {
    setStopError(null);
    const result = await stopRun(runId);
    if (result.ok) {
      setStopped(true);
      closeStream();
    } else {
      // Don't swallow the failure: the run is NOT actually stopped
      // server-side, so don't mark the UI as stopped either.
      setStopError(`Could not stop this run: ${result.message}`);
    }
  };

  const doneCount = plan.filter((t) => t.done || t.status === "done").length;

  const tabItems = useMemo(
    () => [
      { value: "knowledge", label: "Knowledge Base" },
      { value: "plan", label: "Plan" },
      { value: "report", label: "Report", glow: reportJustArrived },
    ],
    [reportJustArrived],
  );

  const pct =
    plan.length > 0 ? Math.min(100, Math.round((doneCount / plan.length) * 100)) : 0;

  if (loadError) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-background px-6">
        <div className="glass-panel flex max-w-md items-start gap-3 rounded-xl p-6 text-error">
          <Icon name="error" className="mt-0.5 shrink-0" />
          <div>
            <p className="font-headline-sm text-headline-sm text-on-surface">
              Could not load this run
            </p>
            <p className="mt-1 text-sm text-error/80">{loadError}</p>
            <Link href="/" className="mt-3 inline-block text-sm text-primary hover:underline">
              &larr; Back to dashboard
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-col overflow-hidden bg-background text-on-surface">
      {/* Top bar */}
      <header className="sticky top-0 z-50 flex h-16 w-full items-center justify-between border-b border-outline-variant/10 bg-surface-container/60 px-6 py-3 backdrop-blur-xl">
        <div className="flex min-w-0 items-center gap-6">
          <Link
            href="/"
            className="shrink-0 font-headline-md text-headline-md font-bold tracking-tight text-on-surface"
          >
            Curator
          </Link>
          <div className="hidden h-6 w-px bg-outline-variant/30 sm:block" />
          <div className="hidden min-w-0 flex-col sm:flex">
            <span className="font-label-caps text-label-caps text-on-surface-variant/60">
              ACTIVE GOAL
            </span>
            <span className="truncate font-headline-sm text-headline-sm">
              {run?.goal ?? "Loading goal…"}
            </span>
          </div>
          {!connected && !isTerminal && (
            <span className="hidden shrink-0 font-label-caps text-label-caps text-warn sm:inline">
              reconnecting…
            </span>
          )}
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-3 rounded-lg bg-primary-container px-4 py-2">
            <Icon name="timer" className="text-primary" />
            <span className="font-code-sm text-code-sm text-primary">
              {formatElapsed(elapsed)}
            </span>
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-outline-variant/20 bg-surface-variant/30 px-3 py-1.5">
            <div className="h-2 w-2 rounded-full bg-primary shadow-[0_0_8px_rgba(193,198,217,0.5)]" />
            <AgentModelSummary snapshot={run?.agent_model_snapshot} className="font-label-caps text-label-caps" />
          </div>
          <div className="hidden items-center gap-2 md:flex">
            <div className="relative h-2 w-32 overflow-hidden rounded-full bg-surface-container-lowest">
              <div
                className={`absolute inset-y-0 left-0 rounded-full transition-all duration-500 ${
                  status === "failed" ? "bg-error" : "bg-gradient-to-r from-primary to-secondary"
                }`}
                style={{ width: `${status === "failed" ? 100 : pct}%` }}
              />
            </div>
            <span className="font-code-sm text-code-sm text-on-surface-variant">
              {pct}%
            </span>
          </div>
          <button
            type="button"
            onClick={handleStop}
            disabled={isTerminal}
            className="flex items-center gap-2 rounded-lg bg-error-container px-4 py-2 text-on-error-container transition-colors hover:bg-error hover:text-on-error active:scale-95 disabled:opacity-40"
          >
            <Icon name="stop_circle" className="text-[20px]" />
            <span className="font-label-caps text-label-caps font-bold">STOP RUN</span>
          </button>
          <NotificationsPanel />
        </div>
      </header>

      {(run?.status === "failed" || streamError || stopError) && (
        <div className="flex flex-col gap-1 border-b border-outline-variant/10 bg-surface-container/40 px-6 py-2">
          {run?.status === "failed" && (
            <div className="flex items-center gap-2 text-xs text-error">
              <Icon name="error" className="shrink-0 text-[16px]" />
              {run?.error || "The run failed."}
            </div>
          )}
          {streamError && (
            <div className="flex items-center gap-2 text-xs text-warn">
              <Icon name="error" className="shrink-0 text-[16px]" />
              {streamError}
            </div>
          )}
          {stopError && (
            <div className="flex items-center gap-2 text-xs text-error">
              <Icon name="error" className="shrink-0 text-[16px]" />
              {stopError}
            </div>
          )}
        </div>
      )}

      <div className="flex flex-1 overflow-hidden">
        {/* Thin icon-only nav rail */}
        <aside className="hidden w-16 flex-col items-center gap-6 border-r border-outline-variant/10 bg-surface-container-lowest py-6 sm:flex">
          <Link
            href="/"
            className="rounded-lg bg-primary-container p-2 text-primary"
            aria-label="Dashboard"
          >
            <Icon name="dashboard" filled />
          </Link>
          <Link
            href="/history"
            className="text-on-surface-variant/50 hover:text-on-surface"
            aria-label="History"
          >
            <Icon name="history" />
          </Link>
          <div className="mt-auto flex flex-col gap-6">
            <Link
              href="/documentation"
              aria-label="Documentation"
              className="text-on-surface-variant/50 hover:text-on-surface"
            >
              <Icon name="menu_book" />
            </Link>
            <Link
              href="/settings"
              aria-label="Settings"
              className="text-on-surface-variant/50 hover:text-on-surface"
            >
              <Icon name="settings" />
            </Link>
          </div>
        </aside>

        {/* 3-column grid — 1px gap on outline-variant doubles as dividers */}
        <main className="grid flex-1 grid-cols-1 gap-px overflow-hidden bg-outline-variant/10 lg:grid-cols-[280px_1fr_360px]">
          {/* Left: Agent panel */}
          <section className="flex flex-col overflow-hidden bg-surface-container-low/60 backdrop-blur-xl">
            <div className="flex items-center justify-between border-b border-outline-variant/10 p-4">
              <span className="font-label-caps text-label-caps opacity-60">
                ACTIVE CREW ({AGENT_TEAM.length})
              </span>
              <Icon name="group_add" className="text-[18px] text-on-surface-variant" />
            </div>
            <div className="scroll-hide flex-1 overflow-y-auto p-4">
              <div className="flex flex-col gap-3">
                {AGENT_TEAM.map((agent) => (
                  <AgentCard
                    key={agent.key}
                    agentKey={agent.key}
                    name={agent.name}
                    role={agent.role}
                    state={agentStates[agent.key]}
                    task={agentTasks[agent.key]}
                  />
                ))}
              </div>
            </div>
          </section>

          {/* Center: per-agent Kanban board */}
          <section className="flex flex-col overflow-hidden bg-background">
            <AgentKanbanBoard
              cardsByAgent={cardsByAgent}
              agentStates={agentStates}
              agentTasks={agentTasks}
              errors={sseErrors}
              onDismissError={(id) =>
                setSseErrors((prev) => prev.filter((e) => e.id !== id))
              }
            />
          </section>

          {/* Right: tabs */}
          <section className="flex flex-col overflow-hidden bg-surface-container-low/60 backdrop-blur-xl">
            <Tabs items={tabItems} value={activeTab} onChange={setActiveTab} />
            <div className="scroll-hide flex-1 overflow-y-auto p-4">
              {activeTab === "knowledge" &&
                (knowledge.length === 0 ? (
                  <p className="text-sm text-on-surface-variant">No notes yet.</p>
                ) : (
                  <div className="flex flex-col gap-3">
                    <span className="font-label-caps text-[11px] opacity-40">
                      SOURCES &amp; ASSETS
                    </span>
                    {knowledge.map((entry, i) => (
                      <KnowledgeCard key={entry.id ?? i} entry={entry} />
                    ))}
                  </div>
                ))}
              {activeTab === "plan" && <PlanChecklist plan={plan} />}
              {activeTab === "report" &&
                (report ? (
                  <ReportView
                    report={report}
                    goal={run?.goal ?? ""}
                    agentModelSnapshot={run?.agent_model_snapshot ?? null}
                  />
                ) : (
                  <p className="text-sm text-on-surface-variant">
                    The report will appear here once synthesis is complete.
                  </p>
                ))}
            </div>
            {/* Phase checklist footer, bound to the real plan */}
            <div className="border-t border-outline-variant/10 bg-surface-container-lowest/40 p-4">
              <span className="mb-3 block font-label-caps text-[10px] uppercase opacity-40">
                {isTerminal
                  ? `Run ${status}`
                  : plan.length > 0
                    ? `Progress: ${doneCount} / ${plan.length} subtasks`
                    : "Current phase: Planning"}
              </span>
              {plan.length === 0 ? (
                <p className="text-[12px] text-on-surface-variant/60">
                  No plan yet — the Supervisor is still thinking.
                </p>
              ) : (
                <div className="flex flex-col gap-2">
                  {plan.slice(0, 6).map((task, i) => {
                    const done = task.done || task.status === "done";
                    return (
                      <div key={task.id ?? i} className="flex items-center gap-2">
                        {done ? (
                          <Icon
                            name="check_circle"
                            filled
                            className="text-[16px] text-primary"
                          />
                        ) : (
                          <span className="h-3.5 w-3.5 rounded-sm border border-outline" />
                        )}
                        <span
                          className={`truncate text-[12px] ${
                            done ? "text-on-surface-variant" : "text-on-surface"
                          }`}
                        >
                          {task.title ?? task.description ?? "Untitled subtask"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}
