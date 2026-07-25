"use client";

import { useState } from "react";
import { Icon } from "@/components/ui/icon";

export function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard API unavailable/denied — silently no-op, snippet is still
      // selectable/readable manually.
    }
  };

  return (
    <button
      type="button"
      onClick={copy}
      aria-label="Copy to clipboard"
      className={`rounded-md p-1.5 text-on-surface-variant transition-colors hover:bg-surface-variant/30 hover:text-on-surface ${className ?? ""}`}
    >
      <Icon name={copied ? "check" : "content_copy"} className="text-[14px]" />
    </button>
  );
}
