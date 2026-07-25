"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Icon } from "@/components/ui/icon";
import { getHealth, listLLMConfigs } from "@/lib/api";

/**
 * The app has no user accounts (documented v1 scope excludes auth), so the
 * avatar circle opens a small live system-status popover instead of a fake
 * profile menu: backend reachability + saved LLM config count, linking to
 * /settings. (Settings no longer carries a single "default provider" — LLM
 * selection is per-run against the saved config list.)
 */
export function StatusPopover() {
  const [open, setOpen] = useState(false);
  const [checked, setChecked] = useState(false);
  const [reachable, setReachable] = useState(false);
  const [configSummary, setConfigSummary] = useState<string | null>(null);
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
        setChecked(false);
        getHealth()
          .then(() => setReachable(true))
          .catch(() => setReachable(false))
          .finally(() => setChecked(true));
        listLLMConfigs()
          .then((configs) => {
            const verified = configs.filter((c) => c.status === "verified").length;
            setConfigSummary(
              configs.length === 0
                ? "None saved"
                : `${configs.length} saved (${verified} verified)`,
            );
          })
          .catch(() => setConfigSummary(null));
      }
      return next;
    });
  };

  return (
    <div className="relative" ref={rootRef}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={open}
        aria-label="System status"
        className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border border-outline-variant/20 bg-secondary-container text-xs font-bold text-on-secondary-container transition-transform hover:scale-105"
      >
        C
      </button>
      {open && (
        <div className="glass-panel absolute right-0 top-12 z-50 w-64 rounded-xl p-4 shadow-2xl">
          <p className="mb-3 font-label-caps text-label-caps text-on-surface-variant">
            System Status
          </p>
          <div className="flex items-center justify-between text-sm">
            <span className="text-on-surface-variant">Backend</span>
            {!checked ? (
              <span className="text-on-surface-variant">Checking…</span>
            ) : reachable ? (
              <span className="flex items-center gap-1 text-emerald-400">
                <Icon name="check_circle" filled className="text-[14px]" />
                Reachable
              </span>
            ) : (
              <span className="flex items-center gap-1 text-error">
                <Icon name="error" className="text-[14px]" />
                Unreachable
              </span>
            )}
          </div>
          <div className="mt-2 flex items-center justify-between text-sm">
            <span className="text-on-surface-variant">LLM configs</span>
            <span className="text-on-surface">{configSummary ?? "—"}</span>
          </div>
          <p className="mt-3 text-[11px] text-on-surface-variant/70">
            No user accounts in this version — this reflects system-level
            status, not a personal profile.
          </p>
          <Link
            href="/settings"
            className="mt-3 flex items-center gap-1 text-sm text-primary hover:underline"
            onClick={() => setOpen(false)}
          >
            <Icon name="settings" className="text-[16px]" />
            Open Settings
          </Link>
        </div>
      )}
    </div>
  );
}
