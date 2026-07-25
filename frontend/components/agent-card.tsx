import { Icon } from "@/components/ui/icon";
import { cn, hexToRgba } from "@/lib/utils";
import type { AgentKey, AgentState } from "@/lib/types";
import { AGENT_TEAM } from "@/lib/types";

const STATE_LABEL: Record<AgentState, string> = {
  idle: "IDLE",
  working: "WORKING",
  done: "DONE",
  flagged: "FLAGGED",
};

export function AgentCard({
  name,
  role,
  agentKey,
  state = "idle",
  task,
  compact = false,
}: {
  name: string;
  role: string;
  agentKey: AgentKey;
  state?: AgentState;
  task?: string;
  compact?: boolean;
}) {
  const meta = AGENT_TEAM.find((a) => a.key === agentKey);
  const color = meta?.color ?? "#8b5cf6";
  const icon = meta?.icon ?? "smart_toy";
  const working = state === "working";
  const label = STATE_LABEL[state];

  return (
    <div
      className={cn(
        "glass-card rounded-xl border-l-4 p-3 transition-all",
        state === "idle" && "opacity-70",
      )}
      style={{ borderLeftColor: color }}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-center gap-2">
          <Icon name={icon} style={{ color }} className="shrink-0" />
          <span className="truncate font-headline-sm text-[15px] text-on-surface">
            {name}
          </span>
        </div>
        <div
          className="flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5"
          style={{
            background: state === "idle" ? undefined : hexToRgba(color, 0.1),
          }}
        >
          <div
            className={cn("h-1.5 w-1.5 rounded-full", working && "animate-breathe")}
            style={{ background: state === "idle" ? undefined : color }}
          />
          <span
            className="text-[10px] font-bold"
            style={{ color: state === "idle" ? undefined : color }}
          >
            {label}
          </span>
        </div>
      </div>

      {!compact && (
        <p className="text-[12px] leading-relaxed text-on-surface-variant">
          {task || role}
        </p>
      )}

      {working && (
        <>
          <div className="mt-2 h-1 w-full rounded-full bg-surface-container-lowest">
            <div
              className="h-full w-2/5 animate-pulse-dot rounded-full"
              style={{ background: color }}
            />
          </div>
          {task && (
            <p className="mt-1 truncate font-code-sm text-[10px] italic text-on-surface-variant/60">
              {task}
            </p>
          )}
        </>
      )}
    </div>
  );
}
