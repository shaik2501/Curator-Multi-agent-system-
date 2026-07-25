"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { listRuns } from "@/lib/api";
import type { RunSummary } from "@/lib/types";
import { formatRelative, parseTimestampMs } from "@/lib/utils";

const LAST_SEEN_KEY = "curator:notifications:lastSeen";

export interface NotificationItem {
  id: string;
  goal: string;
  status: "completed" | "failed";
  timestamp: string | undefined;
  relative: string;
}

function readLastSeen(): number {
  if (typeof window === "undefined") return 0;
  const raw = window.localStorage.getItem(LAST_SEEN_KEY);
  const t = raw ? Number(raw) : 0;
  return Number.isFinite(t) ? t : 0;
}

/**
 * Derives "notifications" from real run data (no fake feed): any run whose
 * status is completed/failed, most recent first. Unread = newer than the
 * last time the user opened the panel, tracked in localStorage.
 */
export function useNotifications() {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [lastSeen, setLastSeen] = useState<number>(0);

  useEffect(() => {
    setLastSeen(readLastSeen());
  }, []);

  const refresh = useCallback(() => {
    listRuns()
      .then((data) => setRuns(data))
      .catch(() => {
        // non-fatal: notifications just stay empty
      })
      .finally(() => setLoaded(true));
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const items: NotificationItem[] = useMemo(() => {
    return runs
      .filter((r) => r.status === "completed" || r.status === "failed")
      .map((r) => ({
        id: r.id,
        goal: r.goal,
        status: r.status as "completed" | "failed",
        timestamp: r.updated_at ?? r.created_at,
        relative: formatRelative(r.updated_at ?? r.created_at),
      }))
      .sort((a, b) => (parseTimestampMs(b.timestamp) ?? 0) - (parseTimestampMs(a.timestamp) ?? 0));
  }, [runs]);

  const unreadCount = useMemo(
    () => items.filter((it) => (parseTimestampMs(it.timestamp) ?? 0) > lastSeen).length,
    [items, lastSeen],
  );

  const markSeen = useCallback(() => {
    const now = Date.now();
    if (typeof window !== "undefined") {
      window.localStorage.setItem(LAST_SEEN_KEY, String(now));
    }
    setLastSeen(now);
  }, []);

  return { items, unreadCount, loaded, markSeen, refresh };
}
