import { cn } from "@/lib/cn";

interface SheetProps {
  open: boolean;
  onClose: () => void;
  children: React.ReactNode;
  className?: string;
}

export function Sheet({ open, onClose, children, className }: SheetProps) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex flex-col justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />
      {/* Panel */}
      <div
        className={cn(
          "relative z-10 rounded-t-2xl border-t border-slate-700 bg-slate-900",
          "max-h-[80vh] overflow-auto",
          className,
        )}
        role="dialog"
        aria-modal="true"
      >
        {children}
      </div>
    </div>
  );
}

export function SheetHeader({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex items-center justify-between border-b border-slate-700 px-4 py-3", className)}
      {...props}
    >
      {children}
    </div>
  );
}

export function SheetTitle({ className, children, ...props }: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2 className={cn("text-base font-semibold text-slate-200", className)} {...props}>
      {children}
    </h2>
  );
}

export function SheetContent({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("p-4", className)} {...props}>
      {children}
    </div>
  );
}
