"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Icon } from "@/components/ui/icon";
import { cn } from "@/lib/utils";

const NAV_ITEMS = [
  { href: "/", label: "Dashboard", icon: "dashboard" },
  { href: "/history", label: "History", icon: "history" },
] as const;

const FOOTER_ITEMS = [
  { href: "/settings", label: "Settings", icon: "settings" },
  { href: "/documentation", label: "Documentation", icon: "menu_book" },
] as const;

/** Desktop left sidebar: logo, Supervisor identity block, nav, footer links. */
export function Sidebar() {
  const pathname = usePathname();
  return (
    <aside className="fixed left-0 top-0 z-50 hidden h-screen w-sidebar-width flex-col border-r border-outline-variant/10 bg-surface-container-low/60 px-gutter py-panel-padding backdrop-blur-xl md:flex">
      <div className="mb-12">
        <Link href="/" className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-on-primary">
            <Icon name="science" filled />
          </div>
          <h1 className="font-headline-md text-headline-md font-black text-on-surface">
            Curator
          </h1>
        </Link>
        <div className="mt-8 flex items-center gap-3 rounded-xl bg-surface-container-highest/40 p-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full border border-primary/20 bg-primary-container text-primary">
            <Icon name="smart_toy" filled />
          </div>
          <div className="min-w-0">
            <p className="truncate font-headline-sm text-headline-sm text-on-surface">
              Supervisor AI
            </p>
            <p className="truncate font-label-caps text-label-caps text-on-surface-variant/70">
              Claude &amp; Ollama
            </p>
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-2">
        {NAV_ITEMS.map((item) => {
          const active = item.href === "/" ? pathname === "/" : pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-4 py-3 transition-all duration-300",
                active
                  ? "border-l-4 border-primary bg-primary-container font-bold text-on-primary-container shadow-sm"
                  : "text-on-surface-variant/70 hover:bg-surface-variant/30 hover:text-on-surface",
              )}
            >
              <Icon name={item.icon} filled={active} />
              <span className="font-label-caps text-label-caps">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto space-y-2 border-t border-outline-variant/10 pt-6">
        {FOOTER_ITEMS.map((item) => {
          const active = pathname?.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-4 py-3 transition-all duration-300",
                active
                  ? "text-on-surface"
                  : "text-on-surface-variant/70 hover:bg-surface-variant/30 hover:text-on-surface",
              )}
            >
              <Icon name={item.icon} filled={active} />
              <span className="font-label-caps text-label-caps">{item.label}</span>
            </Link>
          );
        })}
      </div>
    </aside>
  );
}
