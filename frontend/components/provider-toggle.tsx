"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";
import { PROVIDER_META } from "@/lib/types";
import type { LLMConfig, Provider } from "@/lib/types";

/**
 * Dashboard's primary/simple "which LLM to run with" picker — driven by the
 * user's saved LLMConfig list (GET /api/llm-configs), not a fixed set of
 * provider types. This choice applies to all 7 agent roles by default;
 * `components/dashboard/agent-config-advanced.tsx` lets it be overridden
 * per role before building the POST /api/runs `agent_configs` map.
 */
export function ProviderToggle({
  value,
  onChange,
  configs,
  loading,
  className,
}: {
  value: string | null;
  onChange: (configId: string) => void;
  configs: LLMConfig[];
  loading?: boolean;
  className?: string;
}) {
  const selected = configs.find((c) => c.id === value);

  if (loading) {
    return (
      <div className={cn("text-sm text-on-surface-variant", className)}>
        Loading saved LLM configs…
      </div>
    );
  }

  if (configs.length === 0) {
    return (
      <div className={cn("text-center text-sm text-on-surface-variant", className)}>
        No LLM configs saved yet —{" "}
        <Link href="/settings" className="text-primary hover:underline">
          add one in Settings
        </Link>{" "}
        to start a run.
      </div>
    );
  }

  return (
    <div className={className}>
      <div
        role="tablist"
        aria-label="LLM config"
        className="flex flex-wrap items-center justify-center gap-2 rounded-full border border-outline-variant/30 bg-surface-container-lowest p-1"
      >
        {configs.map((c) => {
          const meta = PROVIDER_META[c.provider_type as Provider];
          const active = value === c.id;
          const verified = c.status === "verified";
          return (
            <button
              key={c.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => onChange(c.id)}
              className={cn(
                "flex items-center gap-1.5 rounded-full px-4 py-2 font-label-caps text-label-caps transition-all",
                active
                  ? "bg-surface-container-highest text-on-surface shadow-sm"
                  : "text-on-surface-variant/50 hover:text-on-surface",
              )}
            >
              <Icon name={meta?.icon ?? "smart_toy"} className="text-[16px]" />
              {c.label || meta?.label || c.provider_type}
              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full",
                  verified
                    ? "bg-emerald-400"
                    : c.status === "failed"
                      ? "bg-error"
                      : "bg-warn",
                )}
                aria-label={c.status}
              />
            </button>
          );
        })}
      </div>
      {selected && selected.status === "failed" && (
        <p className="mt-2 text-center text-xs text-error">
          This key failed verification —{" "}
          <Link href="/settings" className="underline hover:text-on-surface">
            see Settings
          </Link>
          .
        </p>
      )}
      {selected && selected.status === "unverified" && (
        <p className="mt-2 text-center text-xs text-warn">
          This config hasn&apos;t been verified yet —{" "}
          <Link href="/settings" className="underline hover:text-on-surface">
            check it in Settings
          </Link>
          .
        </p>
      )}
    </div>
  );
}
