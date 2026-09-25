import * as React from "react";
import { cn } from "@/lib/utils";

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: "default" | "secondary" | "outline" | "destructive" | "success" | "warning";
}

function Badge({ className, variant = "default", ...props }: BadgeProps) {
  const variants = {
    default: "border-transparent bg-blue-500/10 text-blue-400 border border-blue-500/20",
    secondary: "border-transparent bg-[#1F2937] text-slate-300 border border-[#374151]",
    outline: "text-slate-300 border border-[#1F2937]",
    destructive: "border-transparent bg-rose-500/10 text-rose-400 border border-rose-500/20",
    success: "border-transparent bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    warning: "border-transparent bg-amber-500/10 text-amber-400 border border-amber-500/20",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center rounded px-2 py-0.5 text-[10px] font-medium font-sans transition-colors focus:outline-none focus:ring-1 focus:ring-ring select-none",
        variants[variant],
        className
      )}
      {...props}
    />
  );
}

export { Badge };
