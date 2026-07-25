"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { useNotifications } from "@/lib/use-notifications";

/** Bell button + dropdown, backed by real run data (no mocked feed). */
export function NotificationsPanel() {
  const router = useRouter();
  const { items, unreadCount, loaded, markSeen, refresh } = useNotifications();
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClickAway(e: MouseEvent) {
      if (rootRef.current && !rootRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    if (open) document.addEventListener("mousedown", onClickAway);
    return () => document.removeEventListener("mousedown", onClickAway);
  }, [open]);

  const toggle = () => {
    setOpen((v) => {
      const next = !v;
      if (next) {
        refresh();
        markSeen();
      }
      return next;
    });
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={toggle}
        className="relative rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-variant/20 hover:text-primary"
        aria-label="Notifications"
        aria-expanded={open}
      >
        <Icon name="notifications" />
        {unreadCount > 0 && (
          <span className="absolute right-0.5 top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-error px-1 text-[10px] font-bold text-on-error">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>
      {open && (
        <div className="glass-panel absolute right-0 top-12 z-50 max-h-96 w-80 overflow-y-auto rounded-xl shadow-2xl">
          <div className="border-b border-outline-variant/10 px-4 py-3">
            <span className="font-label-caps text-label-caps text-on-surface-variant">
              Notifications
            </span>
          </div>
          {!loaded ? (
            <p className="p-4 text-sm text-on-surface-variant">Loading…</p>
          ) : items.length === 0 ? (
            <p className="p-4 text-sm text-on-surface-variant">
              No finished runs yet.
            </p>
          ) : (
            <ul className="divide-y divide-outline-variant/10">
              {items.slice(0, 10).map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      setOpen(false);
                      router.push(`/runs/${item.id}`);
                    }}
                    className="flex w-full items-start gap-2 px-4 py-3 text-left transition-colors hover:bg-surface-variant/20"
                  >
                    <Icon
                      name={item.status === "completed" ? "check_circle" : "error"}
                      filled
                      className={`mt-0.5 shrink-0 text-[16px] ${
                        item.status === "completed" ? "text-emerald-400" : "text-error"
                      }`}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block truncate text-sm text-on-surface">
                        {item.goal}
                      </span>
                      <span className="text-xs text-on-surface-variant">
                        {item.status === "completed" ? "Completed" : "Failed"} ·{" "}
                        {item.relative}
                      </span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
