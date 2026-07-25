"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import { Sidebar } from "@/components/shell/sidebar";
import { Topbar } from "@/components/shell/topbar";
import { Icon } from "@/components/ui/icon";

export interface DocSection {
  id: string;
  file: string;
  label: string;
  content: string | null;
}

export default function DocumentationClient({
  sections,
}: {
  sections: DocSection[];
}) {
  const [activeId, setActiveId] = useState(sections[0]?.id ?? "");
  const active = sections.find((s) => s.id === activeId) ?? sections[0];

  return (
    <div className="flex min-h-screen w-full">
      <Sidebar />
      <main className="min-h-screen flex-1 bg-background md:ml-[280px]">
        <Topbar searchPlaceholder="Search…" />
        <div className="mx-auto flex max-w-container-max gap-8 p-8">
          <nav className="hidden w-48 shrink-0 flex-col gap-1 lg:sticky lg:top-20 lg:flex lg:h-fit">
            <p className="mb-2 font-label-caps text-[11px] uppercase tracking-wide text-on-surface-variant">
              Documentation
            </p>
            {sections.map((s) => (
              <button
                key={s.id}
                type="button"
                onClick={() => setActiveId(s.id)}
                className={`flex items-center gap-2 rounded-lg px-3 py-2 text-left text-sm transition-colors ${
                  active?.id === s.id
                    ? "bg-primary-container font-semibold text-on-primary-container"
                    : "text-on-surface-variant hover:bg-surface-variant/20 hover:text-on-surface"
                }`}
              >
                <Icon name="description" className="text-[16px]" />
                {s.label}
              </button>
            ))}
          </nav>

          <div className="min-w-0 flex-1">
            <div className="mb-4 flex items-center gap-2 lg:hidden">
              <select
                value={active?.id}
                onChange={(e) => setActiveId(e.target.value)}
                className="w-full rounded-lg border border-outline-variant/30 bg-surface-container-lowest px-3 py-2 text-sm text-on-surface"
              >
                {sections.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="glass-panel rounded-2xl p-8">
              {active?.content ? (
                <div className="markdown">
                  <ReactMarkdown>{active.content}</ReactMarkdown>
                </div>
              ) : (
                <div className="flex items-start gap-3 text-warn">
                  <Icon name="warning" className="mt-0.5 shrink-0" />
                  <div>
                    <p className="font-headline-sm text-headline-sm text-on-surface">
                      Could not read {active?.file}
                    </p>
                    <p className="mt-1 text-sm text-on-surface-variant">
                      This document is expected at{" "}
                      <code className="rounded bg-surface-container-highest px-1.5 py-0.5 font-code-sm text-code-sm">
                        docs/{active?.file}
                      </code>{" "}
                      relative to the project root.
                    </p>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
