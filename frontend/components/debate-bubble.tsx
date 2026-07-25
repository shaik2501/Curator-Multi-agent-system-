"use client";

import { motion } from "framer-motion";
import { AGENT_TEAM } from "@/lib/types";

const WRITER_COLOR = AGENT_TEAM.find((a) => a.key === "writing")?.color ?? "#f472b6";
const CRITIC_COLOR = AGENT_TEAM.find((a) => a.key === "critic")?.color ?? "#fb923c";

export function DebateBubble({
  role,
  content,
  round,
}: {
  role: "writer" | "critic";
  content: string;
  round?: number;
}) {
  const isWriter = role === "writer";
  const color = isWriter ? WRITER_COLOR : CRITIC_COLOR;
  const label = isWriter ? "Technical Writer" : "Critic";

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.15 }}
      className={`flex w-full ${isWriter ? "justify-start" : "justify-end"}`}
    >
      <div className={`max-w-[85%] flex flex-col ${isWriter ? "" : "items-end"}`}>
        <div
          className={`mb-1 flex items-center gap-2 text-[11px] ${
            isWriter ? "pl-1" : "flex-row-reverse pr-1"
          }`}
        >
          <span className="text-[13px] font-bold" style={{ color }}>
            {label}
          </span>
          {round != null && (
            <span className="font-code-sm text-on-surface-variant/50">
              round {round}
            </span>
          )}
        </div>
        <div
          className={`glass-card rounded-2xl border-surface-container-high/40 bg-surface-container-high/40 p-4 ${
            isWriter
              ? "rounded-tl-none border-l-4"
              : "rounded-tr-none border-r-4 text-right"
          }`}
          style={isWriter ? { borderLeftColor: color } : { borderRightColor: color }}
        >
          <p className="whitespace-pre-wrap text-[14px] text-on-surface">{content}</p>
        </div>
      </div>
    </motion.div>
  );
}
