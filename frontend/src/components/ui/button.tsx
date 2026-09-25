import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
  size?: "default" | "sm" | "lg" | "icon";
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "default", size = "default", ...props }, ref) => {
    const variants = {
      default: "bg-blue-600 text-white hover:bg-blue-500 shadow-sm border border-blue-500/30",
      destructive: "bg-rose-950 text-rose-200 border border-rose-800 hover:bg-rose-900 shadow-sm",
      outline: "border border-[#1F2937] bg-[#111827] text-slate-200 hover:bg-[#1F2937] hover:text-white shadow-sm",
      secondary: "bg-[#1F2937] text-slate-100 hover:bg-[#374151] border border-[#374151]",
      ghost: "hover:bg-[#1F2937] text-slate-300 hover:text-white",
      link: "text-blue-400 underline-offset-4 hover:underline p-0 h-auto",
    };

    const sizes = {
      default: "h-8 px-3 py-1.5 text-xs font-medium rounded",
      sm: "h-7 px-2.5 text-[11px] font-medium rounded",
      lg: "h-9 px-4 text-xs font-semibold rounded",
      icon: "h-8 w-8 text-xs flex items-center justify-center rounded",
    };

    return (
      <button
        className={cn(
          "inline-flex items-center justify-center transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-blue-500 disabled:pointer-events-none disabled:opacity-50 select-none font-sans",
          variants[variant],
          sizes[size],
          className
        )}
        ref={ref}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";

export { Button };
