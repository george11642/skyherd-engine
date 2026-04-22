/**
 * MonoText — JetBrains Mono wrapper for telemetry data, timestamps, hashes.
 */

import { cn } from "@/lib/cn";

export interface MonoTextProps extends React.HTMLAttributes<HTMLSpanElement> {
  dim?: boolean;
  size?: "xs" | "sm" | "md";
}

const SIZE_CLASSES = {
  xs: "text-[0.6875rem] leading-[0.875rem]",
  sm: "text-xs leading-4",
  md: "text-sm leading-5",
};

export function MonoText({
  dim = false,
  size = "sm",
  className,
  children,
  ...props
}: MonoTextProps) {
  return (
    <span
      className={cn(
        "font-mono tabnum tracking-[0.01em]",
        SIZE_CLASSES[size],
        dim ? "text-[rgb(110_122_140)]" : "text-[rgb(168_180_198)]",
        className,
      )}
      style={{ fontFamily: "var(--font-mono)" }}
      {...props}
    >
      {children}
    </span>
  );
}
