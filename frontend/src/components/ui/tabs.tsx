import * as React from "react";
import { cn } from "@/lib/utils";

interface TabsProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
  className?: string;
}

const Tabs = ({ value, onValueChange, children, className }: TabsProps) => {
  return (
    <div className={cn("space-y-4", className)}>
      {React.Children.map(children, (child) => {
        if (React.isValidElement(child)) {
          return React.cloneElement(child as React.ReactElement<any>, {
            activeValue: value,
            onValueChange,
          });
        }
        return child;
      })}
    </div>
  );
};

const TabsList = ({ children, className }: { children: React.ReactNode; className?: string }) => (
  <div className={cn("inline-flex h-9 items-center justify-start rounded-md bg-[#0B0F19] p-1 text-slate-400 border border-[#1F2937]", className)}>
    {children}
  </div>
);

interface TabsTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  value: string;
  activeValue?: string;
  onValueChange?: (value: string) => void;
}

const TabsTrigger = ({ value, activeValue, onValueChange, children, className, ...props }: TabsTriggerProps) => {
  const isActive = activeValue === value;
  return (
    <button
      onClick={() => onValueChange && onValueChange(value)}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1 text-xs font-medium transition-all focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 select-none",
        isActive
          ? "bg-[#1F2937] text-white shadow-sm font-semibold border border-[#374151]"
          : "text-slate-400 hover:text-slate-200 hover:bg-[#1F2937]/50",
        className
      )}
      {...props}
    >
      {children}
    </button>
  );
};

interface TabsContentProps {
  value: string;
  activeValue?: string;
  children: React.ReactNode;
  className?: string;
}

const TabsContent = ({ value, activeValue, children, className }: TabsContentProps) => {
  if (value !== activeValue) return null;
  return <div className={cn("mt-2 outline-none animate-fade-in", className)}>{children}</div>;
};

export { Tabs, TabsList, TabsTrigger, TabsContent };
