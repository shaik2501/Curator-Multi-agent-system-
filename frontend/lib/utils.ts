import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { AGENT_KEYS, type AgentKey } from "./types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Replicates a single saved config id across all 7 agent roles. */
export function buildUniformAgentConfigs(configId: string): Record<AgentKey, string> {
  return AGENT_KEYS.reduce(
    (acc, key) => {
      acc[key] = configId;
      return acc;
    },
    {} as Record<AgentKey, string>,
  );
}

/**
 * Parses an ISO-ish timestamp defensively. If the string has no timezone
 * offset (no trailing Z or +hh:mm/-hh:mm), it's treated as UTC by appending
 * "Z" before parsing — backends sometimes emit naive UTC timestamps.
 * Returns null if the value is missing or unparseable.
 */
export function parseTimestampMs(iso?: string | null): number | null {
  if (!iso) return null;
  const trimmed = iso.trim();
  const hasTz = /Z$|[+-]\d{2}:?\d{2}$/.test(trimmed);
  const normalized = hasTz ? trimmed : `${trimmed}Z`;
  const t = new Date(normalized).getTime();
  return Number.isNaN(t) ? null : t;
}

export function formatDate(iso?: string): string {
  const t = parseTimestampMs(iso);
  if (t == null) return "—";
  return new Date(t).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatElapsed(seconds: number): string {
  const s = Math.max(0, Math.floor(seconds));
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}:${rem.toString().padStart(2, "0")}`;
}

export function formatDuration(seconds?: number): string {
  if (seconds == null || Number.isNaN(seconds)) return "—";
  if (seconds < 60) return `${Math.round(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.round(seconds % 60);
  return `${m}m ${s}s`;
}

/** Relative time (e.g. "2h ago", "Just now") for compact run rows. */
export function formatRelative(iso?: string | null): string {
  const t = parseTimestampMs(iso);
  if (t == null) return "—";
  const diffSec = Math.max(0, (Date.now() - t) / 1000);
  if (diffSec < 60) return "Just now";
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  const days = Math.floor(diffSec / 86400);
  if (days < 7) return `${days}d ago`;
  return formatDate(iso ?? undefined);
}

/** Converts a hex color (#rrggbb) to an rgba() string with the given alpha. */
export function hexToRgba(hex: string, alpha: number): string {
  const clean = hex.replace("#", "");
  const bigint = parseInt(clean, 16);
  const r = (bigint >> 16) & 255;
  const g = (bigint >> 8) & 255;
  const b = bigint & 255;
  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}
