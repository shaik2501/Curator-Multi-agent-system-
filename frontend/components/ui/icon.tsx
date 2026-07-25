import { cn } from "@/lib/utils";

/**
 * Material Symbols Outlined helper. The variable font is loaded globally via
 * a <link> in app/layout.tsx; this renders the ligature span with the right
 * font-variation-settings for weight/fill.
 */
export function Icon({
  name,
  filled = false,
  weight = 400,
  className,
  style,
}: {
  name: string;
  filled?: boolean;
  weight?: number;
  className?: string;
  style?: React.CSSProperties;
}) {
  return (
    <span
      className={cn("material-symbols-outlined select-none", className)}
      style={{
        fontVariationSettings: `'FILL' ${filled ? 1 : 0}, 'wght' ${weight}, 'GRAD' 0, 'opsz' 24`,
        ...style,
      }}
      aria-hidden="true"
    >
      {name}
    </span>
  );
}
