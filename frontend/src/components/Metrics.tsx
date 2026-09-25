import React from 'react';

interface MetricsProps {
  total: number;
  active: number;
  escalated: number;
  resolved: number;
}

export const Metrics: React.FC<MetricsProps> = ({ total, active, escalated, resolved }) => {
  return (
    <div className="bg-white border border-slate-200 rounded-md px-4 py-3 flex flex-wrap items-center justify-between gap-4 font-sans text-xs">
      <div className="flex items-center space-x-6 text-xs divide-x divide-slate-200">
        <div className="flex items-center gap-2">
          <span className="text-slate-500 uppercase tracking-wider text-[10px] font-medium font-sans">Open Exceptions</span>
          <span className="font-mono font-bold text-slate-900 text-sm">{active}</span>
        </div>

        <div className="pl-6 flex items-center gap-2">
          <span className="text-slate-500 uppercase tracking-wider text-[10px] font-medium font-sans">Awaiting Verification</span>
          <span className="font-mono font-bold text-slate-900 text-sm">3</span>
        </div>

        <div className="pl-6 flex items-center gap-2">
          <span className="text-slate-500 uppercase tracking-wider text-[10px] font-medium font-sans">Escalated</span>
          <span className="font-mono font-bold text-rose-700 text-sm">{escalated}</span>
        </div>

        <div className="pl-6 flex items-center gap-2">
          <span className="text-slate-500 uppercase tracking-wider text-[10px] font-medium font-sans">Resolved Today</span>
          <span className="font-mono font-bold text-emerald-700 text-sm">{resolved}</span>
        </div>
      </div>

      <div className="text-[11px] font-mono text-slate-400">
        Total Stream: <span className="font-semibold text-slate-700">{total}</span>
      </div>
    </div>
  );
};

