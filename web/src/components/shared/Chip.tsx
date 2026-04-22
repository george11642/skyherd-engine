/**
 * Chip — monospace status badge used throughout the dashboard.
 * Variants map to the brand color palette.
 */

import { cn } from "@/lib/cn";

export type ChipVariant =
  | "sage"
  | "sky"
  | "dust"
  | "thermal"
  | "warn"
  | "danger"
  | "muted";

export interface ChipProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: ChipVariant;
  dot?: boolean;
  pulse?: boolean;
}

const DOT_COLORS: Record<ChipVariant, string> = {
  sage:    "bg-[rgb(148_176_136)]",
  sky:     "bg-[rgb(120_180_220)]",
  dust:    "bg-[rgb(210_178_138)]",
  thermal: "bg-[rgb(255_143_60)]",
  warn:    "bg-[rgb(240_195_80)]",
  danger:  "bg-[rgb(224_100_90)]",
  muted:   "bg-[rgb(110_122_140)]",
};

export function Chip({
  variant = "muted",
  dot = false,
  pulse = false,
  className,
  children,
  ...props
}: ChipProps) {
  return (
    <span
      className={cn(`chip chip-${variant}`, className)}
      {...props}
    >
      {dot && (
        <span
          className={cn(
            "inline-block h-1.5 w-1.5 rounded-full shrink-0",
            DOT_COLORS[variant],
            pulse && "pulse-dot",
          )}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}
