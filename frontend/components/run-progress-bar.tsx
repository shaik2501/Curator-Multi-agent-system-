export function RunProgressBar({
  done,
  total,
  status,
  className,
}: {
  done: number;
  total: number;
  /** Run status; when terminal, the phase label is replaced (not "Planning…"). */
  status?: string;
  className?: string;
}) {
  const pct = total > 0 ? Math.min(100, Math.round((done / total) * 100)) : 0;

  let label: string;
  let labelClass = "text-inkMuted";
  let barClass = "bg-hero-gradient";
  if (status === "failed") {
    label = "Failed";
    labelClass = "text-danger";
    barClass = "bg-danger";
  } else if (status === "completed") {
    label = "Completed";
    labelClass = "text-success";
    barClass = "bg-success";
  } else if (status === "stopped") {
    label = "Stopped";
    labelClass = "text-warn";
    barClass = "bg-warn";
  } else {
    // Phase labels (Planning… / x / y subtasks) are reserved for running runs.
    label = total > 0 ? `${done} / ${total} subtasks` : "Planning…";
  }

  return (
    <div className={className}>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className={labelClass}>{label}</span>
        <span className="text-inkMuted">{pct}%</span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface2">
        <div
          className={`h-full rounded-full ${barClass} transition-all duration-500`}
          style={{ width: `${status === "failed" ? 100 : pct}%` }}
        />
      </div>
    </div>
  );
}
