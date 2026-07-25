"use client";

import { useCallback, useRef, useState } from "react";
import { Icon } from "@/components/ui/icon";

export interface ConfirmOptions {
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  /** Styles the Confirm button with the danger/error token. Defaults to true
   * since confirm() is typically used for destructive actions. */
  danger?: boolean;
}

interface ConfirmState extends ConfirmOptions {
  open: boolean;
}

const DEFAULT_STATE: ConfirmState = {
  open: false,
  message: "",
};

/**
 * In-app replacement for window.confirm(). Call `confirm(message)` (or pass
 * a full ConfirmOptions object) from an event handler; it resolves to
 * `true`/`false` once the user picks Confirm/Cancel in the styled modal.
 * Render `<dialog />` once, anywhere in the component tree that uses this.
 *
 *   const { confirm, dialog } = useConfirm();
 *   ...
 *   if (!(await confirm("Delete this item?"))) return;
 *   ...
 *   return <>{dialog}{...rest}</>;
 */
export function useConfirm() {
  const [state, setState] = useState<ConfirmState>(DEFAULT_STATE);
  const resolverRef = useRef<((value: boolean) => void) | null>(null);

  const confirm = useCallback((opts: ConfirmOptions | string) => {
    const options: ConfirmOptions = typeof opts === "string" ? { message: opts } : opts;
    setState({ open: true, ...options });
    return new Promise<boolean>((resolve) => {
      resolverRef.current = resolve;
    });
  }, []);

  const settle = useCallback((value: boolean) => {
    setState(DEFAULT_STATE);
    resolverRef.current?.(value);
    resolverRef.current = null;
  }, []);

  const dialog = (
    <ConfirmDialog
      open={state.open}
      title={state.title}
      message={state.message}
      confirmLabel={state.confirmLabel}
      cancelLabel={state.cancelLabel}
      danger={state.danger}
      onConfirm={() => settle(true)}
      onCancel={() => settle(false)}
    />
  );

  return { confirm, dialog };
}

export function ConfirmDialog({
  open,
  title = "Are you sure?",
  message,
  confirmLabel = "Confirm",
  cancelLabel = "Cancel",
  danger = true,
  onConfirm,
  onCancel,
}: {
  open: boolean;
  title?: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}) {
  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      role="presentation"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onCancel();
      }}
    >
      <div
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-message"
        className="glass-panel w-full max-w-sm rounded-2xl p-6 shadow-2xl"
      >
        <div className="mb-3 flex items-center gap-2">
          <Icon
            name={danger ? "warning" : "help"}
            className={danger ? "text-error" : "text-primary"}
          />
          <h2 id="confirm-dialog-title" className="font-headline-sm text-headline-sm text-on-surface">
            {title}
          </h2>
        </div>
        <p id="confirm-dialog-message" className="text-sm text-on-surface-variant">
          {message}
        </p>
        <div className="mt-6 flex justify-end gap-2">
          <button
            type="button"
            autoFocus
            onClick={onCancel}
            className="rounded-lg border border-outline-variant/20 bg-surface-container-high px-4 py-2 text-sm font-medium text-on-surface transition-colors hover:bg-surface-variant/30"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className={
              danger
                ? "rounded-lg bg-error px-4 py-2 text-sm font-semibold text-on-error transition-opacity hover:opacity-90"
                : "rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-on-primary transition-opacity hover:opacity-90"
            }
          >
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
