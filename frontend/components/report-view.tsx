"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import ReactMarkdown from "react-markdown";
import { Icon } from "@/components/ui/icon";
import { ApiError, createRun } from "@/lib/api";
import { AGENT_KEYS } from "@/lib/types";
import type { AgentKey, AgentModelSnapshot } from "@/lib/types";

interface Heading {
  id: string;
  text: string;
  level: number;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\s-]/g, "")
    .replace(/\s+/g, "-");
}

function extractHeadings(markdown: string): Heading[] {
  const lines = markdown.split("\n");
  const headings: Heading[] = [];
  for (const line of lines) {
    const match = /^(#{1,3})\s+(.*)/.exec(line);
    if (match) {
      const level = match[1].length;
      const text = match[2].trim();
      headings.push({ id: slugify(text), text, level });
    }
  }
  return headings;
}

function downloadMarkdown(filename: string, content: string) {
  const blob = new Blob([content], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export function ReportView({
  report,
  goal,
  agentModelSnapshot,
}: {
  report: string;
  goal: string;
  /** This run's per-agent LLM assignment — reused as-is for the follow-up run. */
  agentModelSnapshot: Partial<Record<AgentKey, AgentModelSnapshot>> | null;
}) {
  const router = useRouter();
  const [followUp, setFollowUp] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const headings = useMemo(() => extractHeadings(report), [report]);

  // Rebuild the same agent_configs map this run used; fall back to
  // Supervisor's config for any role that's somehow missing (shouldn't
  // normally happen since the backend always snapshots all 7).
  const fallbackConfigId = agentModelSnapshot?.supervisor?.config_id;
  const canReuse = AGENT_KEYS.every(
    (key) => agentModelSnapshot?.[key]?.config_id || fallbackConfigId,
  );

  const submitFollowUp = async () => {
    if (!followUp.trim() || submitting) return;
    if (!canReuse) {
      setError("This run has no known LLM config to reuse for a follow-up.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const seededGoal = `Follow-up to previous research: "${goal}"\n\nPrevious report context:\n${report.slice(
        0,
        4000,
      )}\n\nFollow-up question: ${followUp.trim()}`;
      const agentConfigs = AGENT_KEYS.reduce(
        (acc, key) => {
          acc[key] = (agentModelSnapshot?.[key]?.config_id || fallbackConfigId)!;
          return acc;
        },
        {} as Record<AgentKey, string>,
      );
      const { run_id } = await createRun(seededGoal, agentConfigs);
      router.push(`/runs/${run_id}`);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Could not start follow-up run.",
      );
      setSubmitting(false);
    }
  };

  return (
    <div className="flex flex-col gap-4 lg:flex-row">
      {headings.length > 0 && (
        <aside className="order-2 hidden shrink-0 lg:sticky lg:top-20 lg:order-1 lg:block lg:h-fit lg:w-48">
          <p className="mb-2 font-label-caps text-[11px] uppercase tracking-wide text-on-surface-variant">
            Contents
          </p>
          <ul className="flex flex-col gap-1 text-xs">
            {headings.map((h) => (
              <li key={h.id} style={{ paddingLeft: (h.level - 1) * 10 }}>
                <a
                  href={`#${h.id}`}
                  className="text-on-surface-variant hover:text-primary"
                >
                  {h.text}
                </a>
              </li>
            ))}
          </ul>
        </aside>
      )}

      <div className="order-1 min-w-0 flex-1 lg:order-2">
        <div className="mb-4 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-on-surface-variant">
            <Icon name="description" className="text-[18px]" />
            <span className="text-sm">Final report</span>
          </div>
          <button
            type="button"
            onClick={() => downloadMarkdown("research-report.md", report)}
            className="flex items-center gap-2 rounded-lg border border-outline-variant/20 bg-surface-container-high px-3 py-1.5 text-xs font-medium text-on-surface transition-colors hover:bg-surface-variant/30"
          >
            <Icon name="download" className="text-[16px]" />
            Download .md
          </button>
        </div>

        <div className="markdown">
          <ReactMarkdown
            components={{
              h1: ({ children, ...props }) => (
                <h1 id={slugify(String(children))} {...props}>
                  {children}
                </h1>
              ),
              h2: ({ children, ...props }) => (
                <h2 id={slugify(String(children))} {...props}>
                  {children}
                </h2>
              ),
              h3: ({ children, ...props }) => (
                <h3 id={slugify(String(children))} {...props}>
                  {children}
                </h3>
              ),
              a: ({ children, ...props }) => (
                <a target="_blank" rel="noopener noreferrer" {...props}>
                  {children}
                </a>
              ),
            }}
          >
            {report}
          </ReactMarkdown>
        </div>

        <div className="mt-8 glass-card rounded-xl p-4">
          <p className="mb-2 text-sm font-medium text-on-surface">Ask a follow-up</p>
          <div className="flex gap-2">
            <input
              value={followUp}
              onChange={(e) => setFollowUp(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") submitFollowUp();
              }}
              placeholder="e.g. Dig deeper into pricing comparisons…"
              className="flex-1 rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface placeholder:text-on-surface-variant/50 focus:border-primary focus:outline-none"
            />
            <button
              type="button"
              onClick={submitFollowUp}
              disabled={!followUp.trim() || submitting || !canReuse}
              className="flex items-center gap-2 rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90 disabled:opacity-40"
            >
              <Icon name="send" className="text-[16px]" />
              {submitting ? "Starting…" : "Ask"}
            </button>
          </div>
          {error && <p className="mt-2 text-xs text-error">{error}</p>}
        </div>
      </div>
    </div>
  );
}
