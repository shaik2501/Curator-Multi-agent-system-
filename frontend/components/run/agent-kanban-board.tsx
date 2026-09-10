"use client";
import Image from "next/image";

import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Icon } from "@/components/ui/icon";
import { AGENT_TEAM } from "@/lib/types";
import type { AgentKey, AgentState } from "@/lib/types";
import { cn, hexToRgba } from "@/lib/utils";
import { API_BASE_URL } from "@/lib/api";

export type KanbanCardKind =
  | "supervisor_turn"
  | "task_result"
  | "note"
  | "writer_revision"
  | "critic_turn"
  | "report"
  | "error";

export interface KanbanCard {
  id: string;
  kind: KanbanCardKind;
  title: string;
  subtitle?: string;
  body?: string;
  timestamp?: string;
  /** Path from GET /api/images/{run_id}/{filename}, relative to API_BASE_URL. */
  imageUrl?: string;
}

function CardImage({ src }: { src: string }) {
  const [status, setStatus] = useState<"loading" | "loaded" | "error">("loading");
  const fullSrc = src.startsWith("http") ? src : `${API_BASE_URL}${src}`;
  return (
    <div className="relative mb-1.5 overflow-hidden rounded-md bg-surface-container-lowest">
      {status === "error" ? (
        <div className="flex h-24 flex-col items-center justify-center gap-1 text-on-surface-variant/50">
          <Icon name="broken_image" className="text-[18px]" />
          <p className="text-[10px]">Image unavailable</p>
        </div>
      ) : (
        <>
          {status === "loading" && (
            <div className="flex h-24 items-center justify-center">
              <Icon name="sync" className="animate-spin text-[18px] text-on-surface-variant/50" />
            </div>
          )}
          <Image width={0} height={0} sizes="100vw" style={{width: "100%", height: "auto"}} unoptimized={true}
            src={fullSrc}
            alt=""
            onLoad={() => setStatus("loaded")}
            onError={() => setStatus("error")}
            className={cn(
              "w-full max-h-48 object-contain",
              status === "loading" && "hidden",
            )}
          />
        </>
      )}
    </div>
  );
}

const STATE_LABEL: Record<AgentState, string> = {
  idle: "IDLE",
  working: "WORKING",
  done: "DONE",
  flagged: "FLAGGED",
};

const KIND_ICON: Record<KanbanCardKind, string> = {
  supervisor_turn: "alt_route",
  task_result: "fact_check",
  note: "chat_bubble",
  writer_revision: "history_edu",
  critic_turn: "gavel",
  report: "auto_awesome",
  error: "error",
};

function Column({
  agentKey,
  cards,
  state,
  task,
}: {
  agentKey: AgentKey;
  cards: KanbanCard[];
  state: AgentState;
  task?: string;
}) {
  const meta = AGENT_TEAM.find((a) => a.key === agentKey)!;
  const bodyRef = useRef<HTMLDivElement>(null);
  const working = state === "working";

  useEffect(() => {
    const el = bodyRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [cards.length]);

  return (
    <div className="glass-card flex h-full w-72 shrink-0 flex-col overflow-hidden rounded-xl">
      <div
        className="flex flex-col gap-2 border-b border-outline-variant/10 p-3"
        style={{ background: hexToRgba(meta.color, 0.08) }}
      >
        <div className="flex items-center justify-between gap-2">
          <div className="flex min-w-0 items-center gap-2">
            <Icon name={meta.icon} style={{ color: meta.color }} className="shrink-0" />
            <span className="truncate font-headline-sm text-[14px] text-on-surface">
              {meta.name}
            </span>
          </div>
          <div
            className="flex shrink-0 items-center gap-1.5 rounded-full px-2 py-0.5"
            style={{ background: state === "idle" ? undefined : hexToRgba(meta.color, 0.15) }}
          >
            <div
              className={cn("h-1.5 w-1.5 rounded-full", working && "animate-breathe")}
              style={{ background: state === "idle" ? undefined : meta.color }}
            />
            <span
              className="text-[9px] font-bold"
              style={{ color: state === "idle" ? undefined : meta.color }}
            >
              {STATE_LABEL[state]}
            </span>
          </div>
        </div>
        {working && task && (
          <p className="truncate font-code-sm text-[10px] italic text-on-surface-variant/70">
            {task}
          </p>
        )}
      </div>

      <div ref={bodyRef} className="scroll-hide flex-1 overflow-y-auto p-2">
        {cards.length === 0 ? (
          <div className="flex h-full min-h-[120px] flex-col items-center justify-center gap-1 text-center text-on-surface-variant/50">
            <Icon name={meta.icon} className="text-[20px] opacity-40" />
            <p className="text-[11px]">No activity yet</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            <div className="flex flex-col gap-2">
              {cards.map((card) => (
                <motion.div
                  key={card.id}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.15 }}
                  className="rounded-lg border border-outline-variant/10 bg-surface-container-high/40 p-2.5"
                >
                  <div className="mb-1 flex items-center gap-1.5">
                    <Icon
                      name={KIND_ICON[card.kind]}
                      className="text-[13px]"
                      style={{ color: card.kind === "error" ? undefined : meta.color }}
                    />
                    <span className="truncate text-[11px] font-bold text-on-surface">
                      {card.title}
                    </span>
                  </div>
                  {card.subtitle && (
                    <p className="mb-1 text-[10px] italic text-on-surface-variant/70">
                      {card.subtitle}
                    </p>
                  )}
                  {card.imageUrl && <CardImage src={card.imageUrl} />}
                  {card.body && (
                    <p className="whitespace-pre-wrap text-[11px] leading-relaxed text-on-surface-variant">
                      {card.body}
                    </p>
                  )}
                  {card.timestamp && (
                    <p className="mt-1 font-code-sm text-[9px] text-on-surface-variant/50">
                      {new Date(card.timestamp).toLocaleTimeString(undefined, {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </p>
                  )}
                </motion.div>
              ))}
            </div>
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}

export function AgentKanbanBoard({
  cardsByAgent,
  agentStates,
  agentTasks,
  errors,
  onDismissError,
}: {
  cardsByAgent: Record<AgentKey, KanbanCard[]>;
  agentStates: Record<AgentKey, AgentState>;
  agentTasks: Partial<Record<AgentKey, string>>;
  errors: { id: string; message: string }[];
  onDismissError: (id: string) => void;
}) {
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-outline-variant/10 p-4">
        <Icon name="view_kanban" className="text-primary" />
        <span className="font-headline-sm text-headline-sm text-on-surface">
          Agent Activity Board
        </span>
      </div>

      {errors.length > 0 && (
        <div className="flex flex-col gap-1 border-b border-outline-variant/10 p-2">
          {errors.map((err) => (
            <div
              key={err.id}
              className="flex items-center justify-between gap-2 rounded-lg border border-error/30 bg-error/10 px-3 py-2 text-xs text-error"
            >
              <span className="flex items-center gap-2">
                <Icon name="error" className="shrink-0 text-[14px]" />
                {err.message}
              </span>
              <button
                type="button"
                onClick={() => onDismissError(err.id)}
                aria-label="Dismiss"
                className="shrink-0 text-error/70 hover:text-error"
              >
                <Icon name="close" className="text-[14px]" />
              </button>
            </div>
          ))}
        </div>
      )}

      <div
        aria-live="polite"
        className="scroll-hide flex flex-1 gap-3 overflow-x-auto p-4"
      >
        {AGENT_TEAM.map((agent) => (
          <Column
            key={agent.key}
            agentKey={agent.key}
            cards={cardsByAgent[agent.key] ?? []}
            state={agentStates[agent.key]}
            task={agentTasks[agent.key]}
          />
        ))}
      </div>
    </div>
  );
}
