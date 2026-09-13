"use client";

import { useState } from "react";
import Image from "next/image";
import { Icon } from "@/components/ui/icon";
import type { KnowledgeEntry, NoteSource } from "@/lib/types";
import { API_BASE_URL } from "@/lib/api";

function normalizeSources(sources?: NoteSource[] | string[]): NoteSource[] {
  if (!sources) return [];
  return sources.map((s) => (typeof s === "string" ? { url: s } : s));
}

export function KnowledgeCard({ entry }: { entry: KnowledgeEntry }) {
  const sources = normalizeSources(entry.sources);
  const agentLabel = (entry.agent ?? "agent").toUpperCase();
  const [imgStatus, setImgStatus] = useState<"loading" | "loaded" | "error">("loading");
  const imageSrc = entry.image_url
    ? entry.image_url.startsWith("http")
      ? entry.image_url
      : `${API_BASE_URL}${entry.image_url}`
    : null;

  return (
    <div className="glass-card rounded-xl p-3">
      <div className="mb-2 flex items-center justify-between">
        <span className="rounded bg-primary-container px-2 py-0.5 text-[10px] font-bold text-primary">
          {agentLabel}
        </span>
        {entry.created_at && (
          <span className="font-code-sm text-[10px] text-on-surface-variant">
            {new Date(entry.created_at).toLocaleTimeString(undefined, {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      {imageSrc && (
        <div className="relative mb-2 overflow-hidden rounded-md bg-surface-container-lowest">
          {imgStatus === "error" ? (
            <div className="flex h-24 flex-col items-center justify-center gap-1 text-on-surface-variant/50">
              <Icon name="broken_image" className="text-[18px]" />
              <p className="text-[10px]">Image unavailable</p>
            </div>
          ) : (
            <>
              {imgStatus === "loading" && (
                <div className="flex h-24 items-center justify-center">
                  <Icon name="sync" className="animate-spin text-[18px] text-on-surface-variant/50" />
                </div>
              )}
              <div className={`relative h-56 w-full ${imgStatus === "loading" ? "opacity-0 absolute" : "opacity-100"}`}>
                <Image
                  unoptimized={true}
                  fill
                  src={imageSrc}
                  alt=""
                  onLoad={() => setImgStatus("loaded")}
                  onError={() => setImgStatus("error")}
                  className="object-contain"
                />
              </div>
            </>
          )}
        </div>
      )}

      <p className="mb-2 line-clamp-3 text-[13px] text-on-surface">
        {entry.content ?? (imageSrc ? "" : "—")}
      </p>
      {sources.length > 0 && (
        <div className="mt-2 flex flex-col gap-1">
          {sources.map((s, i) => (
            <a
              key={i}
              href={s.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-1 truncate text-[11px] text-primary hover:underline"
            >
              <Icon name="link" className="shrink-0 text-[14px]" />
              <span className="truncate">{s.title || s.url}</span>
            </a>
          ))}
        </div>
      )}
    </div>
  );
}
