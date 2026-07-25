"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icon";
import { AGENT_TEAM, PROVIDER_META } from "@/lib/types";
import type { AgentModelSnapshot, AgentKey, Provider } from "@/lib/types";

/**
 * Compact display of a run's per-agent LLM assignments: shows Supervisor's
 * model as the primary label, with a hover/click popover listing all 7 —
 * a full 7-model row everywhere would be cluttered.
 */
export function AgentModelSummary({
  snapshot,
  className,
}: {
  snapshot?: Partial<Record<AgentKey, AgentModelSnapshot>> | null;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const entries = AGENT_TEAM.map((a) => ({ agent: a, model: snapshot?.[a.key] }));
  const primary = snapshot?.supervisor;
  const primaryMeta = primary ? PROVIDER_META[primary.provider_type as Provider] : undefined;
  const distinctCount = new Set(
    entries.map((e) => e.model?.config_id).filter((v): v is string => Boolean(v)),
  ).size;

  if (!snapshot || Object.keys(snapshot).length === 0) {
    return <span className={`text-sm text-on-surface-variant ${className ?? ""}`}>—</span>;
  }

  return (
    <div
      className={`relative inline-block ${className ?? ""}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <button
        type="button"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
        className="flex items-center gap-1.5 text-sm text-on-surface-variant hover:text-on-surface"
      >
        <Icon name={primaryMeta?.icon ?? "smart_toy"} className="text-[14px]" />
        <span>{primary?.label || primaryMeta?.label || primary?.provider_type || "—"}</span>
        {distinctCount > 1 && (
          <span className="rounded-full bg-primary/10 px-1.5 py-0.5 text-[10px] font-bold text-primary">
            +{distinctCount - 1}
          </span>
        )}
      </button>
      {open && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="glass-panel absolute left-0 top-7 z-50 w-64 rounded-xl p-3 shadow-2xl"
        >
          <p className="mb-2 font-label-caps text-[10px] uppercase tracking-wide text-on-surface-variant">
            Per-agent models
          </p>
          <div className="flex flex-col gap-1.5">
            {entries.map(({ agent, model }) => {
              const meta = model ? PROVIDER_META[model.provider_type as Provider] : undefined;
              return (
                <div key={agent.key} className="flex items-center justify-between gap-2 text-xs">
                  <span className="flex items-center gap-1.5 text-on-surface-variant">
                    <Icon name={agent.icon} style={{ color: agent.color }} className="text-[13px]" />
                    {agent.name}
                  </span>
                  <span className="truncate text-on-surface">
                    {model ? model.label || meta?.label || model.provider_type : "—"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
