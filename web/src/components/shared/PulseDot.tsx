/**
 * PulseDot — a small animated dot indicating live/active status.
 */

import { cn } from "@/lib/cn";

export type PulseDotColor = "sage" | "thermal" | "warn" | "danger" | "sky" | "muted";

const COLOR_CLASSES: Record<PulseDotColor, string> = {
  sage:    "bg-[rgb(148_176_136)]",
  thermal: "bg-[rgb(255_143_60)]",
  warn:    "bg-[rgb(240_195_80)]",
  danger:  "bg-[rgb(224_100_90)]",
  sky:     "bg-[rgb(120_180_220)]",
  muted:   "bg-[rgb(110_122_140)]",
};

export interface PulseDotProps {
  color?: PulseDotColor;
  size?: "sm" | "md";
  active?: boolean;
  className?: string;
}

export function PulseDot({
  color = "sage",
  size = "sm",
  active = true,
  className,
}: PulseDotProps) {
  return (
    <span
      className={cn(
        "inline-block rounded-full shrink-0",
        size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2",
        active ? COLOR_CLASSES[color] : "bg-[rgb(38_45_58)]",
        active && "pulse-dot",
        className,
      )}
      aria-hidden="true"
    />
  );
}
