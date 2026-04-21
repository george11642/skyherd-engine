import { cn } from "@/lib/cn";

type ButtonVariant = "default" | "outline" | "ghost" | "destructive";
type ButtonSize = "sm" | "md" | "lg" | "icon";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  default:
    "bg-blue-600 text-white hover:bg-blue-700 border border-blue-700 shadow-sm",
  outline:
    "border border-slate-600 text-slate-300 hover:bg-slate-700 hover:text-slate-100",
  ghost: "text-slate-400 hover:bg-slate-700 hover:text-slate-200",
  destructive: "bg-red-600 text-white hover:bg-red-700 border border-red-700",
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: "px-2.5 py-1.5 text-xs",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-2.5 text-base",
  icon: "h-8 w-8 p-0",
};

export function Button({
  variant = "default",
  size = "md",
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500",
        "disabled:pointer-events-none disabled:opacity-50",
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
