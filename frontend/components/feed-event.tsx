"use client";

import { motion } from "framer-motion";
import { Icon } from "@/components/ui/icon";
import { AGENT_TEAM } from "@/lib/types";
import type { AgentKey } from "@/lib/types";
import { hexToRgba } from "@/lib/utils";

function agentMeta(agent?: string) {
  const found = AGENT_TEAM.find(
    (a) => a.key === (agent as AgentKey) || a.name.toLowerCase() === agent?.toLowerCase(),
  );
  return {
    name: found?.name ?? agent ?? "System",
    color: found?.color ?? "#909096",
    icon: found?.icon ?? "bolt",
  };
}

const KIND_ICON: Record<string, string> = {
  started: "bolt",
  message: "chat_bubble",
  note: "fact_check",
  error: "error",
};

export interface FeedEventData {
  id: string;
  agent?: string;
  message: string;
  timestamp?: string;
  kind?: "started" | "message" | "note" | "error";
  last?: boolean;
}

export function FeedEvent({ event }: { event: FeedEventData }) {
  const { name, color, icon } = agentMeta(event.agent);
  const isError = event.kind === "error";
  const dotColor = isError ? "#ffb4ab" : color;
  const dotIcon = event.kind ? KIND_ICON[event.kind] ?? icon : icon;
  const time = event.timestamp
    ? new Date(event.timestamp).toLocaleTimeString(undefined, {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
      })
    : "";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className="flex gap-4"
    >
      <div className="flex flex-col items-center">
        <div
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border"
          style={{
            borderColor: hexToRgba(dotColor, 0.3),
            background: hexToRgba(dotColor, 0.15),
          }}
        >
          <Icon name={dotIcon} className="text-[16px]" style={{ color: dotColor }} />
        </div>
        {!event.last && <div className="mt-2 w-0.5 flex-1 bg-outline-variant/20" />}
      </div>
      <div className="min-w-0 flex-1 pb-4">
        <div className="mb-1 flex items-center gap-2">
          <span className="text-[13px] font-bold" style={{ color }}>
            {name}
          </span>
          {time && (
            <span className="font-code-sm text-[11px] text-on-surface-variant/50">
              {time}
            </span>
          )}
        </div>
        <div
          className="glass-card rounded-lg p-3 text-sm text-on-surface"
          style={{ background: hexToRgba(dotColor, 0.05) }}
        >
          {event.message}
        </div>
      </div>
    </motion.div>
  );
}
