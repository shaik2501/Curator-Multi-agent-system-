"use client";

import * as React from "react";
import { cn } from "@/lib/utils";

export interface TabItem {
  value: string;
  label: string;
  glow?: boolean;
}

interface TabsProps {
  items: TabItem[];
  value: string;
  onChange: (value: string) => void;
  className?: string;
}

export function Tabs({ items, value, onChange, className }: TabsProps) {
  return (
    <div
      role="tablist"
      className={cn("flex border-b border-outline-variant/10", className)}
    >
      {items.map((item) => {
        const active = item.value === value;
        return (
          <button
            key={item.value}
            role="tab"
            aria-selected={active}
            onClick={() => onChange(item.value)}
            className={cn(
              "flex-1 py-4 font-label-caps text-[12px] uppercase transition-colors",
              active
                ? "border-b-2 border-primary font-bold text-primary"
                : "text-on-surface-variant/50 hover:text-on-surface",
              item.glow && "animate-glow-sweep",
            )}
          >
            {item.label}
          </button>
        );
      })}
    </div>
  );
}
