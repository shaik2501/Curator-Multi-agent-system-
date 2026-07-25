"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { Icon } from "@/components/ui/icon";
import { StatusChip } from "@/components/status-chip";
import { AgentModelSummary } from "@/components/agent-model-summary";
import { ApiError, listRuns } from "@/lib/api";
import { PROVIDER_KEYS, PROVIDER_META } from "@/lib/types";
import type { Provider, RunStatus, RunSummary } from "@/lib/types";
import { formatDate, formatDuration } from "@/lib/utils";

type StatusFilter = "all" | "running" | "completed" | "failed";
type ProviderFilter = "all" | Provider;

export default function HistoryClient() {
  const router = useRouter();
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [providerFilter, setProviderFilter] = useState<ProviderFilter>("all");
  const [filterOpen, setFilterOpen] = useState(false);
  const filterRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickAway(e: MouseEvent) {
      if (filterRef.current && !filterRef.current.contains(e.target as Node)) {
        setFilterOpen(false);
      }
    }
    if (filterOpen) document.addEventListener("mousedown", onClickAway);
    return () => document.removeEventListener("mousedown", onClickAway);
  }, [filterOpen]);

  useEffect(() => {
    let cancelled = false;
    listRuns()
      .then((data) => {
        if (!cancelled) setRuns(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(
            err instanceof ApiError
              ? err.message
              : "Could not load run history.",
          );
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Only metrics we can honestly derive from real /api/runs data.
  const stats = useMemo(() => {
    const total = runs.length;
    const completed = runs.filter((r) => r.status === "completed");
    const durations = completed
      .map((r) => r.duration_seconds)
      .filter((d): d is number => typeof d === "number" && !Number.isNaN(d));
    const avgDuration =
      durations.length > 0
        ? durations.reduce((a, b) => a + b, 0) / durations.length
        : undefined;
    return { total, completedCount: completed.length, avgDuration };
  }, [runs]);

  const filteredRuns = useMemo(() => {
    const q = search.trim().toLowerCase();
    return runs.filter((r) => {
      if (q && !r.goal?.toLowerCase().includes(q)) return false;
      if (statusFilter !== "all") {
        const s = (r.status as RunStatus)?.toString();
        if (statusFilter === "running") {
          if (s !== "running" && s !== "pending") return false;
        } else if (s !== statusFilter) {
          return false;
        }
      }
      if (providerFilter !== "all") {
        const usesProvider = Object.values(r.agent_model_snapshot ?? {}).some(
          (m) => m?.provider_type === providerFilter,
        );
        if (!usesProvider) return false;
      }
      return true;
    });
  }, [runs, search, statusFilter, providerFilter]);

  const activeFilterCount =
    (statusFilter !== "all" ? 1 : 0) + (providerFilter !== "all" ? 1 : 0);

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <main className="relative min-h-screen flex-1 overflow-hidden bg-background md:ml-[280px]">
        <Topbar
          searchPlaceholder="Search past research runs..."
          searchValue={search}
          onSearchChange={setSearch}
        />

        <div className="mx-auto max-w-container-max space-y-8 p-8">
          {/* Page header */}
          <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <h2 className="font-headline-md text-headline-md font-bold tracking-tight text-on-surface">
                Research History
              </h2>
              <p className="mt-1 font-body-md text-body-md text-on-surface-variant/80">
                {loading
                  ? "Loading your research cycles…"
                  : stats.total === 0
                    ? "No research cycles yet."
                    : `Audit and review ${stats.total} research ${
                        stats.total === 1 ? "cycle" : "cycles"
                      } and agent debates.`}
              </p>
            </div>
            <div className="flex gap-3">
              <div className="relative" ref={filterRef}>
                <button
                  type="button"
                  onClick={() => setFilterOpen((v) => !v)}
                  aria-expanded={filterOpen}
                  className="flex items-center gap-2 rounded-lg border border-outline-variant/20 bg-surface-container-high px-4 py-2 font-body-md text-body-md text-on-surface transition-all hover:bg-surface-variant/30"
                >
                  <Icon name="filter_list" className="text-[18px]" />
                  Filter
                  {activeFilterCount > 0 && (
                    <span className="flex h-4 min-w-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-bold text-on-primary">
                      {activeFilterCount}
                    </span>
                  )}
                </button>
                {filterOpen && (
                  <div className="glass-panel absolute right-0 top-12 z-50 w-56 rounded-xl p-4 shadow-2xl">
                    <p className="mb-2 font-label-caps text-label-caps text-on-surface-variant">
                      Status
                    </p>
                    <div className="mb-4 flex flex-wrap gap-1.5">
                      {(["all", "running", "completed", "failed"] as StatusFilter[]).map(
                        (opt) => (
                          <button
                            key={opt}
                            type="button"
                            onClick={() => setStatusFilter(opt)}
                            className={`rounded-full px-3 py-1 text-xs capitalize transition-colors ${
                              statusFilter === opt
                                ? "bg-primary text-on-primary"
                                : "bg-surface-variant/30 text-on-surface-variant hover:text-on-surface"
                            }`}
                          >
                            {opt}
                          </button>
                        ),
                      )}
                    </div>
                    <p className="mb-2 font-label-caps text-label-caps text-on-surface-variant">
                      Provider
                    </p>
                    <div className="flex flex-wrap gap-1.5">
                      {(["all", ...PROVIDER_KEYS] as ProviderFilter[]).map((opt) => (
                        <button
                          key={opt}
                          type="button"
                          onClick={() => setProviderFilter(opt)}
                          className={`rounded-full px-3 py-1 text-xs capitalize transition-colors ${
                            providerFilter === opt
                              ? "bg-primary text-on-primary"
                              : "bg-surface-variant/30 text-on-surface-variant hover:text-on-surface"
                          }`}
                        >
                          {opt === "all" ? "all" : PROVIDER_META[opt].label}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => router.push("/")}
                className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 font-body-md text-body-md font-semibold text-on-primary transition-all hover:opacity-90 active:scale-95"
              >
                <Icon name="add" />
                New Research
              </button>
            </div>
          </div>

          {error && (
            <div className="flex items-center gap-2 rounded-lg border border-error/30 bg-error/10 px-4 py-3 text-sm text-error">
              <Icon name="error" />
              {error}
            </div>
          )}

          {/* Table panel */}
          <div className="glass-panel overflow-hidden rounded-2xl shadow-2xl">
            <div className="overflow-x-auto">
              {loading ? (
                <div className="p-6 text-sm text-on-surface-variant">Loading…</div>
              ) : runs.length === 0 ? (
                <div className="p-6 text-sm text-on-surface-variant">
                  No runs yet. Start your first research from the dashboard.
                </div>
              ) : filteredRuns.length === 0 ? (
                <div className="p-6 text-sm text-on-surface-variant">
                  No runs match the current search/filters.
                </div>
              ) : (
                <table className="w-full border-collapse text-left">
                  <thead>
                    <tr className="border-b border-outline-variant/10 bg-surface-container-lowest/30">
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Status
                      </th>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Research Goal
                      </th>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Provider
                      </th>
                      <th className="px-6 py-4 font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Timestamp
                      </th>
                      <th className="px-6 py-4 text-right font-label-caps text-label-caps uppercase tracking-wider text-on-surface-variant">
                        Actions
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-outline-variant/5">
                    {filteredRuns.map((run) => (
                      <tr
                        key={run.id}
                        className="group cursor-pointer transition-colors hover:bg-surface-variant/10"
                        onClick={() => router.push(`/runs/${run.id}`)}
                      >
                        <td className="px-6 py-5">
                          <StatusChip status={run.status} />
                        </td>
                        <td className="px-6 py-5">
                          <p className="max-w-xs truncate font-body-md text-body-md font-semibold text-on-surface">
                            {run.goal}
                          </p>
                          <p className="mt-0.5 font-code-sm text-[12px] text-on-surface-variant/60">
                            {run.id}
                          </p>
                        </td>
                        <td className="px-6 py-5" onClick={(e) => e.stopPropagation()}>
                          <AgentModelSummary snapshot={run.agent_model_snapshot} />
                        </td>
                        <td className="px-6 py-5">
                          <p className="font-body-md text-body-md text-on-surface">
                            {formatDate(run.created_at)}
                          </p>
                          <p className="text-[12px] text-on-surface-variant/60">
                            {formatDuration(run.duration_seconds)}
                          </p>
                        </td>
                        <td className="px-6 py-5 text-right">
                          <div className="flex justify-end gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                router.push(`/runs/${run.id}`);
                              }}
                              className="rounded-lg p-2 text-on-surface-variant transition-colors hover:bg-primary/20 hover:text-primary"
                              aria-label="View run"
                            >
                              <Icon name="visibility" className="text-[20px]" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            {!loading && runs.length > 0 && (
              <div className="flex items-center justify-between border-t border-outline-variant/10 bg-surface-container-low/40 px-6 py-4">
                <p className="font-body-md text-[13px] text-on-surface-variant">
                  Showing{" "}
                  <span className="font-bold text-on-surface">{filteredRuns.length}</span> of{" "}
                  {runs.length} {runs.length === 1 ? "result" : "results"}
                </p>
              </div>
            )}
          </div>

          {/* Summary — only metrics honestly derivable from real run data. */}
          {!loading && runs.length > 0 && (
            <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
              <div className="glass-card flex flex-col gap-1 rounded-2xl p-6">
                <div className="mb-2 flex items-start justify-between">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Icon name="data_usage" />
                  </span>
                </div>
                <p className="font-label-caps text-label-caps uppercase tracking-widest text-on-surface-variant">
                  Total Runs
                </p>
                <h3 className="mt-1 font-display-lg text-[32px] font-bold text-on-surface">
                  {stats.total}
                </h3>
              </div>
              <div className="glass-card flex flex-col gap-1 rounded-2xl p-6">
                <div className="mb-2 flex items-start justify-between">
                  <span className="rounded-lg bg-tertiary/10 p-2 text-tertiary">
                    <Icon name="timer" />
                  </span>
                </div>
                <p className="font-label-caps text-label-caps uppercase tracking-widest text-on-surface-variant">
                  Avg Duration (Completed)
                </p>
                <h3 className="mt-1 font-display-lg text-[32px] font-bold text-on-surface">
                  {formatDuration(stats.avgDuration)}
                </h3>
              </div>
              <div className="glass-card flex flex-col gap-1 rounded-2xl p-6">
                <div className="mb-2 flex items-start justify-between">
                  <span className="rounded-lg bg-primary/10 p-2 text-primary">
                    <Icon name="hub" />
                  </span>
                </div>
                <p className="font-label-caps text-label-caps uppercase tracking-widest text-on-surface-variant">
                  Completed Runs
                </p>
                <h3 className="mt-1 font-display-lg text-[32px] font-bold text-on-surface">
                  {stats.completedCount}
                </h3>
              </div>
            </div>
          )}
        </div>

        <div className="pointer-events-none absolute -right-24 -top-24 h-96 w-96 rounded-full bg-primary/5 blur-[120px]" />
        <div className="pointer-events-none absolute -bottom-24 -left-24 h-96 w-96 rounded-full bg-tertiary/5 blur-[120px]" />
      </main>
    </div>
  );
}
