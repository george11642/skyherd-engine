import { useState } from "react";
import { cn } from "@/lib/cn";

interface TooltipProps {
  content: string;
  children: React.ReactNode;
  className?: string;
}

export function Tooltip({ content, children, className }: TooltipProps) {
  const [visible, setVisible] = useState(false);

  return (
    <span
      className="relative inline-flex"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onFocus={() => setVisible(true)}
      onBlur={() => setVisible(false)}
    >
      {children}
      {visible && (
        <span
          className={cn(
            "absolute bottom-full left-1/2 z-50 mb-1.5 -translate-x-1/2",
            "whitespace-nowrap rounded-md bg-slate-900 px-2.5 py-1.5",
            "border border-slate-700 text-xs text-slate-200 shadow-xl",
            className,
          )}
          role="tooltip"
        >
          {content}
        </span>
      )}
    </span>
  );
}
