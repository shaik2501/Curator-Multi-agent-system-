"use client";

import { useRouter } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { NotificationsPanel } from "@/components/notifications/notifications-panel";
import { StatusPopover } from "@/components/shell/status-popover";

/** Sticky top bar: real search filter + notifications + settings + status popover. */
export function Topbar({
  searchPlaceholder,
  searchValue,
  onSearchChange,
}: {
  searchPlaceholder: string;
  searchValue?: string;
  onSearchChange?: (value: string) => void;
}) {
  const router = useRouter();
  return (
    <header className="sticky top-0 z-40 flex h-16 w-full items-center justify-between border-b border-outline-variant/10 bg-surface-container/60 px-6 py-3 backdrop-blur-xl">
      <div className="flex items-center gap-4">
        <div className="hidden items-center gap-2 rounded-lg border border-outline-variant/20 bg-surface-container-lowest px-3 py-1.5 md:flex">
          <Icon name="search" className="text-[16px] text-on-surface-variant" />
          <input
            value={searchValue ?? ""}
            onChange={(e) => onSearchChange?.(e.target.value)}
            className="w-48 border-none bg-transparent text-body-md text-on-surface placeholder:text-on-surface-variant/50 focus:outline-none focus:ring-0"
            placeholder={searchPlaceholder}
            type="text"
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <NotificationsPanel />
        <button
          className="rounded-full p-2 text-on-surface-variant transition-colors hover:bg-surface-variant/20 hover:text-primary"
          type="button"
          aria-label="Settings"
          onClick={() => router.push("/settings")}
        >
          <Icon name="settings" />
        </button>
        <StatusPopover />
      </div>
    </header>
  );
}
