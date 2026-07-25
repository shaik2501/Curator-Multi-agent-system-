import type { RunStatus } from "@/lib/types";

const STATUS_STYLES: Record<
  string,
  { label: string; text: string; bg: string; dot: string; pulse?: boolean }
> = {
  pending: {
    label: "Pending",
    text: "text-on-surface-variant",
    bg: "bg-surface-variant/30",
    dot: "bg-on-surface-variant",
  },
  running: {
    label: "Processing",
    text: "text-primary",
    bg: "bg-primary/10",
    dot: "bg-primary",
    pulse: true,
  },
  completed: {
    label: "Completed",
    text: "text-emerald-400",
    bg: "bg-emerald-500/10",
    dot: "bg-emerald-500",
  },
  failed: {
    label: "Failed",
    text: "text-error",
    bg: "bg-error/10",
    dot: "bg-error",
  },
  stopped: {
    label: "Stopped",
    text: "text-warn",
    bg: "bg-warn/10",
    dot: "bg-warn",
  },
};

export function StatusChip({ status }: { status?: RunStatus }) {
  const key = (status || "pending").toString();
  const style = STATUS_STYLES[key] ?? {
    label: key,
    text: "text-on-surface-variant",
    bg: "bg-surface-variant/30",
    dot: "bg-on-surface-variant",
  };
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-semibold capitalize ${style.bg} ${style.text}`}
    >
      <span
        className={`h-1.5 w-1.5 rounded-full ${style.dot} ${style.pulse ? "animate-pulse-dot" : ""}`}
      />
      {style.label}
    </span>
  );
}
