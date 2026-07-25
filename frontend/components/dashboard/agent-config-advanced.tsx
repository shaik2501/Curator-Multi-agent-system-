"use client";

import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { AGENT_TEAM, PROVIDER_META } from "@/lib/types";
import type { AgentKey, LLMConfig, Provider } from "@/lib/types";

/**
 * "Advanced: customize per agent" panel — 8 dropdowns, one per AGENT_KEYS
 * role, each independently overridable against the primary picker's choice.
 * The Image role's dropdown additionally disables any config where
 * `image_capable` is false — the backend 400s a run otherwise.
 */
export function AgentConfigAdvanced({
  open,
  onToggle,
  configs,
  effective,
  onChange,
}: {
  open: boolean;
  onToggle: () => void;
  configs: LLMConfig[];
  /** Effective config id per role (override, falling back to the primary pick). */
  effective: Record<AgentKey, string | null>;
  onChange: (agent: AgentKey, configId: string) => void;
}) {
  const imageCapableConfigs = configs.filter((c) => c.image_capable);

  return (
    <div className="w-full max-w-2xl">
      <button
        type="button"
        onClick={onToggle}
        className="mx-auto flex items-center gap-1 text-xs text-on-surface-variant hover:text-on-surface"
      >
        <Icon name={open ? "expand_less" : "expand_more"} className="text-[16px]" />
        Advanced: customize per agent
      </button>
      {open && (
        <div className="glass-card mt-3 grid grid-cols-1 gap-3 rounded-xl p-4 text-left sm:grid-cols-2">
          {AGENT_TEAM.map((agent) => {
            const isImage = agent.key === "image";
            const value = effective[agent.key] ?? "";

            if (isImage && imageCapableConfigs.length === 0) {
              return (
                <div key={agent.key} className="flex flex-col gap-1 sm:col-span-2">
                  <span className="flex items-center gap-1.5 text-xs font-medium text-on-surface-variant">
                    <Icon name={agent.icon} style={{ color: agent.color }} className="text-[14px]" />
                    {agent.name}
                  </span>
                  <p className="rounded-lg border border-warn/20 bg-warn/5 px-2.5 py-1.5 text-[11px] text-warn">
                    Add an OpenAI or Gemini key in{" "}
                    <Link href="/settings" className="underline hover:text-on-surface">
                      Settings
                    </Link>{" "}
                    to enable image generation.
                  </p>
                </div>
              );
            }

            return (
              <label key={agent.key} className="flex flex-col gap-1">
                <span className="flex items-center gap-1.5 text-xs font-medium text-on-surface-variant">
                  <Icon name={agent.icon} style={{ color: agent.color }} className="text-[14px]" />
                  {agent.name}
                </span>
                <select
                  value={value}
                  onChange={(e) => onChange(agent.key, e.target.value)}
                  className="rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-2.5 py-1.5 text-xs text-on-surface focus:border-primary focus:outline-none"
                >
                  {configs.length === 0 && <option value="">No configs saved</option>}
                  {configs.map((c) => {
                    const meta = PROVIDER_META[c.provider_type as Provider];
                    const label = c.label || meta?.label || c.provider_type;
                    const disabled = isImage && !c.image_capable;
                    return (
                      <option key={c.id} value={c.id} disabled={disabled}>
                        {disabled
                          ? `${label} — not available for image generation`
                          : label + (c.status !== "verified" ? ` (${c.status})` : "")}
                      </option>
                    );
                  })}
                </select>
                {isImage && (
                  <span className="text-[10px] text-on-surface-variant/60">
                    Only OpenAI/Gemini (or image-capable custom) configs can generate images.
                  </span>
                )}
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
}
