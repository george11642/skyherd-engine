import { cn } from "@/lib/cn";

type BadgeVariant = "default" | "success" | "warning" | "destructive" | "outline" | "muted";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
}

const variantClasses: Record<BadgeVariant, string> = {
  default: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  success: "bg-green-500/20 text-green-400 border border-green-500/30",
  warning: "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30",
  destructive: "bg-red-500/20 text-red-400 border border-red-500/30",
  outline: "border border-slate-600 text-slate-400",
  muted: "bg-slate-700/50 text-slate-400 border border-slate-700",
};

export function Badge({ variant = "default", className, children, ...props }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        variantClasses[variant],
        className,
      )}
      {...props}
    >
      {children}
    </span>
  );
}
