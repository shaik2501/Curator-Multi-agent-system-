"use client";

import { useEffect, useRef, useState } from "react";
import { AnimatePresence } from "framer-motion";
import { FeedEvent, type FeedEventData } from "@/components/feed-event";
import { DebateBubble } from "@/components/debate-bubble";
import { Icon } from "@/components/ui/icon";

export type FeedItem =
  | ({ type: "event" } & FeedEventData)
  | {
      type: "debate";
      id: string;
      role: "writer" | "critic";
      content: string;
      round?: number;
    };

export function ActivityFeed({ items }: { items: FeedItem[] }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);

  useEffect(() => {
    if (paused) return;
    const el = containerRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [items, paused]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-outline-variant/10 p-4">
        <Icon name="stream" className="text-primary" />
        <span className="font-headline-sm text-headline-sm text-on-surface">
          Activity Feed
        </span>
      </div>
      <div
        ref={containerRef}
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        aria-live="polite"
        className="scroll-hide flex-1 overflow-y-auto p-6"
      >
        {items.length === 0 && (
          <p className="py-8 text-center text-sm text-on-surface-variant">
            Waiting for the team to start…
          </p>
        )}
        <AnimatePresence initial={false}>
          <div className="flex flex-col gap-2">
            {items.map((item, i) =>
              item.type === "event" ? (
                <FeedEvent
                  key={item.id}
                  event={{ ...item, last: i === items.length - 1 }}
                />
              ) : (
                <DebateBubble
                  key={item.id}
                  role={item.role}
                  content={item.content}
                  round={item.round}
                />
              ),
            )}
          </div>
        </AnimatePresence>
      </div>
    </div>
  );
}
