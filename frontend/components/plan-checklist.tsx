import { Icon } from "@/components/ui/icon";
import type { Subtask } from "@/lib/types";

export function PlanChecklist({ plan }: { plan: Subtask[] }) {
  if (plan.length === 0) {
    return (
      <p className="p-4 text-sm text-on-surface-variant">
        No plan yet — the Supervisor is still thinking.
      </p>
    );
  }
  return (
    <ul className="flex flex-col gap-2 p-4">
      {plan.map((task, i) => {
        const done = task.done || task.status === "done";
        return (
          <li
            key={task.id ?? i}
            className="glass-card flex items-start gap-2 rounded-lg p-3"
          >
            {done ? (
              <Icon
                name="check_circle"
                filled
                className="mt-0.5 shrink-0 text-[16px] text-primary"
              />
            ) : (
              <span className="mt-0.5 h-3.5 w-3.5 shrink-0 rounded-full border border-outline" />
            )}
            <div className="min-w-0">
              <p className="text-sm text-on-surface">
                {task.title ?? task.description ?? "Untitled subtask"}
              </p>
              {task.assigned_to && (
                <p className="text-xs capitalize text-on-surface-variant">
                  {task.assigned_to}
                </p>
              )}
            </div>
          </li>
        );
      })}
    </ul>
  );
}
