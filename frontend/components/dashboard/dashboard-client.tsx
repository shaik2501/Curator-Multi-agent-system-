"use client";

import { useEffect, useMemo, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { Icon } from "@/components/ui/icon";
import { ProviderToggle } from "@/components/provider-toggle";
import { StatusChip } from "@/components/status-chip";
import { AGENT_KEYS, AGENT_TEAM } from "@/lib/types";
import type { AgentKey, RunSummary } from "@/lib/types";
import { ApiError, createRun, listRuns } from "@/lib/api";
import { useLLMConfigs } from "@/lib/use-llm-configs";
import { formatDate, formatDuration, hexToRgba, buildUniformAgentConfigs } from "@/lib/utils";
import { AgentConfigAdvanced } from "@/components/dashboard/agent-config-advanced";

const STATUS_DOT: Record<string, string> = {
  completed: "bg-emerald-500",
  running: "bg-primary",
  pending: "bg-primary",
  failed: "bg-error",
  stopped: "bg-warn",
};

export default function DashboardClient() {
  const router = useRouter();
  const [goal, setGoal] = useState("");
  const [selectedConfigId, setSelectedConfigId] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [runsError, setRunsError] = useState<string | null>(null);
  const [loadingRuns, setLoadingRuns] = useState(true);
  const [search, setSearch] = useState("");
  const { configs, loading: loadingConfigs } = useLLMConfigs();

  // Advanced: per-agent overrides against the primary picker's choice. Only
  // roles explicitly touched here diverge from `selectedConfigId`.
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [agentOverrides, setAgentOverrides] = useState<Partial<Record<AgentKey, string>>>({});

  // Default the selection to the first saved config once configs load (e.g.
  // the backend-seeded Claude config), preferring an already-verified one.
  useEffect(() => {
    if (selectedConfigId || configs.length === 0) return;
    const verified = configs.find((c) => c.status === "verified");
    setSelectedConfigId((verified ?? configs[0]).id);
  }, [configs, selectedConfigId]);

  const imageCapableConfigs = configs.filter((c) => c.image_capable);
  // The image role can't take a non-image-capable config (the backend 400s
  // it) — never silently fall back to the primary pick for it. Default to
  // the first image-capable config if one exists; otherwise it's genuinely
  // unfillable until the user adds one.
  const defaultImageConfigId = imageCapableConfigs[0]?.id ?? null;

  const effectiveAgentConfigs: Record<AgentKey, string | null> = AGENT_KEYS.reduce(
    (acc, key) => {
      if (key === "image") {
        acc[key] = agentOverrides.image ?? defaultImageConfigId;
      } else {
        acc[key] = agentOverrides[key] ?? selectedConfigId;
      }
      return acc;
    },
    {} as Record<AgentKey, string | null>,
  );

  const imageRoleConfigId = effectiveAgentConfigs.image;
  const imageRoleReady = Boolean(
    imageRoleConfigId && configs.find((c) => c.id === imageRoleConfigId)?.image_capable,
  );

  const filteredRuns = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return runs;
    return runs.filter((r) => r.goal?.toLowerCase().includes(q));
  }, [runs, search]);

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setRunsError(
            err instanceof ApiError ? err.message : "Could not load run history.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingRuns(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const submit = useCallback(async () => {
    if (!goal.trim() || submitting || !selectedConfigId || !imageRoleReady) return;
    setSubmitting(true);
    setError(null);
    try {
      // Build the complete 8-key map: the primary pick replicated
      // everywhere, then the image-capable default/override and any other
      // per-agent overrides applied on top.
      const agentConfigs = {
        ...buildUniformAgentConfigs(selectedConfigId),
        ...agentOverrides,
        image: imageRoleConfigId as string,
      };
      const { run_id } = await createRun(goal.trim(), agentConfigs);
      router.push(`/runs/${run_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Something went wrong starting the run.",
      );
      setSubmitting(false);
    }
  }, [goal, selectedConfigId, agentOverrides, imageRoleConfigId, imageRoleReady, submitting, router]);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <main className="flex h-screen flex-1 flex-col overflow-y-auto bg-background md:ml-[280px]">
        <Topbar
          searchPlaceholder="Search research history..."
          searchValue={search}
          onSearchChange={setSearch}
        />

        <div className="mx-auto w-full max-w-container-max space-y-12 p-8">
          {/* Hero */}
          <section className="glass-panel relative flex min-h-[400px] flex-col items-center justify-center space-y-8 overflow-hidden rounded-3xl p-12 text-center">
            <div className="relative z-10 max-w-3xl space-y-4">
              <h2 className="font-display-lg text-display-lg tracking-tight text-on-surface">
                What do you want to research today?
              </h2>
              <p className="mx-auto max-w-xl font-body-lg text-body-lg text-on-surface-variant">
                Assemble your specialist AI crew and dive into deep market
                analysis, technical due diligence, or academic verification.
              </p>
            </div>

            <div className="group relative z-10 w-full max-w-2xl">
              <div className="flex items-center rounded-2xl border border-outline-variant bg-surface-container-lowest p-2 shadow-xl transition-all focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/20">
                <Icon name="rocket_launch" className="ml-4 text-outline" />
                <input
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  onKeyDown={(e) => {
                    if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
                      e.preventDefault();
                      submit();
                    }
                  }}
                  placeholder="e.g. Compare the top 3 vector databases for a startup"
                  type="text"
                  className="flex-1 border-none bg-transparent px-4 py-4 font-headline-sm text-headline-sm text-on-surface placeholder:text-on-surface-variant/40 focus:outline-none focus:ring-0"
                />
                <button
                  onClick={submit}
                  disabled={!goal.trim() || submitting || !selectedConfigId || !imageRoleReady}
                  className="flex items-center gap-2 rounded-xl bg-primary px-8 py-3 font-headline-sm font-bold text-primary-container transition-all hover:bg-primary-fixed-dim active:scale-95 disabled:opacity-50"
                >
                  {submitting ? "Starting…" : "Launch"}
                  <Icon name="arrow_forward" />
                </button>
              </div>
              <p className="mt-2 text-xs text-on-surface-variant/60">
                Tip: press <kbd className="rounded bg-surface-container-highest px-1">Ctrl/⌘</kbd>{" "}
                + <kbd className="rounded bg-surface-container-highest px-1">Enter</kbd> to launch.
              </p>
              {!imageRoleReady && configs.length > 0 && (
                <p className="mt-2 text-xs text-warn">
                  No image-capable LLM config available for the Image agent — add an
                  OpenAI or Gemini key in Settings before launching.
                </p>
              )}
              {error && (
                <div className="mt-4 flex items-center gap-2 rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-left text-sm text-error">
                  <Icon name="error" />
                  {error}
                </div>
              )}
            </div>

            <ProviderToggle
              value={selectedConfigId}
              onChange={setSelectedConfigId}
              configs={configs}
              loading={loadingConfigs}
              className="relative z-10"
            />

            <AgentConfigAdvanced
              open={advancedOpen}
              onToggle={() => setAdvancedOpen((v) => !v)}
              configs={configs}
              effective={effectiveAgentConfigs}
              onChange={(agent, configId) =>
                setAgentOverrides((prev) => ({ ...prev, [agent]: configId }))
              }
            />
          </section>

          {/* Agent team */}
          <section className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="flex items-center gap-3 font-headline-md text-headline-md text-on-surface">
                <Icon name="groups" className="text-primary" />
                Active Specialist Crew
              </h3>
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {AGENT_TEAM.map((agent) => (
                <div
                  key={agent.key}
                  className="glass-panel agent-card group rounded-2xl border-l-4 p-6 transition-all hover:-translate-y-0.5"
                  style={{ borderLeftColor: agent.color }}
                >
                  <div className="mb-4 flex items-start justify-between">
                    <div
                      className="flex h-12 w-12 items-center justify-center rounded-xl"
                      style={{ background: hexToRgba(agent.color, 0.1) }}
                    >
                      <Icon name={agent.icon} style={{ color: agent.color }} />
                    </div>
                    <div
                      className="rounded px-2 py-1 text-[10px] font-bold uppercase tracking-widest"
                      style={{
                        background: hexToRgba(agent.color, 0.2),
                        color: agent.color,
                      }}
                    >
                      {agent.category}
                    </div>
                  </div>
                  <h4 className="mb-2 font-headline-sm text-headline-sm text-on-surface">
                    {agent.name}
                  </h4>
                  <p className="line-clamp-2 text-body-md text-on-surface-variant/80">
                    {agent.role}
                  </p>
                </div>
              ))}
            </div>
          </section>

          {/* Recent runs */}
          <section className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="font-headline-md text-headline-md text-on-surface">
                Recent Research Cycles
              </h3>
            </div>
            {runsError && (
              <div className="flex items-center gap-2 rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
                <Icon name="error" />
                {runsError}
              </div>
            )}
            <div className="glass-panel overflow-hidden rounded-2xl border border-outline-variant/10">
              {loadingRuns ? (
                <div className="p-6 text-sm text-on-surface-variant">Loading…</div>
              ) : runs.length === 0 ? (
                <div className="p-6 text-sm text-on-surface-variant">
                  No runs yet. Start your first research above.
                </div>
              ) : filteredRuns.length === 0 ? (
                <div className="p-6 text-sm text-on-surface-variant">
                  No runs match &ldquo;{search}&rdquo;.
                </div>
              ) : (
                <table className="w-full text-left">
                  <thead className="bg-surface-container-high/40">
                    <tr>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Research Goal
                      </th>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Status
                      </th>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Duration
                      </th>
                      <th className="px-6 py-4 text-right font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Date
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/10">
                    {filteredRuns.slice(0, 8).map((run) => (
                      <tr
                        key={run.id}
                        onClick={() => router.push(`/runs/${run.id}`)}
                        className="group cursor-pointer transition-colors hover:bg-surface-variant/20"
                      >
                        <td className="px-6 py-5">
                          <div className="flex items-center gap-3">
                            <div
                              className={`h-2 w-2 shrink-0 rounded-full ${
                                STATUS_DOT[run.status?.toString() ?? ""] ?? "bg-on-surface-variant"
                              }`}
                            />
                            <span className="truncate font-medium text-on-surface">
                              {run.goal}
                            </span>
                          </div>
                        </td>
                        <td className="px-6 py-5">
                          <StatusChip status={run.status} />
                        </td>
                        <td className="px-6 py-5 font-code-sm text-code-sm text-on-surface-variant">
                          {formatDuration(run.duration_seconds)}
                        </td>
                        <td className="px-6 py-5 text-right font-body-md text-on-surface-variant">
                          {formatDate(run.created_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
