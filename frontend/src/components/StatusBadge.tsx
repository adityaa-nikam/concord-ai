import React from 'react';
import { CaseStatus, PriorityLevel } from '@/lib/types';
import { Badge } from '@/components/ui/badge';
import { Clock, CheckCircle2, AlertCircle, RefreshCw, ShieldAlert } from 'lucide-react';

interface StatusBadgeProps {
  status: CaseStatus | string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status }) => {
  const getBadgeProps = () => {
    switch (status) {
      case 'NEW':
        return {
          className: "bg-slate-100 text-slate-700 border-slate-200",
          icon: <Clock className="w-3 h-3 text-slate-500" />
        };
      case 'INVESTIGATING':
        return {
          className: "bg-amber-50 text-amber-800 border-amber-200",
          icon: <Clock className="w-3 h-3 text-amber-600" />
        };
      case 'POLICY_CHECK':
      case 'RECONCILING':
        return {
          className: "bg-amber-50 text-amber-800 border-amber-200",
          icon: <RefreshCw className="w-3 h-3 text-amber-600" />
        };
      case 'ACTION_REQUIRED':
      case 'ACTION_IN_PROGRESS':
      case 'VERIFYING':
        return {
          className: "bg-blue-50 text-blue-700 border-blue-200",
          icon: <Clock className="w-3 h-3 text-blue-600" />
        };
      case 'RESOLVED':
        return {
          className: "bg-emerald-50 text-emerald-800 border-emerald-200",
          icon: <CheckCircle2 className="w-3 h-3 text-emerald-600" />
        };
      case 'ESCALATED':
        return {
          className: "bg-rose-50 text-rose-800 border-rose-200",
          icon: <AlertCircle className="w-3 h-3 text-rose-600" />
        };
      case 'FAILED':
        return {
          className: "bg-slate-100 text-slate-600 border-slate-200",
          icon: <ShieldAlert className="w-3 h-3 text-slate-500" />
        };
      default:
        return {
          className: "bg-slate-100 text-slate-700 border-slate-200",
          icon: <Clock className="w-3 h-3 text-slate-500" />
        };
    }
  };

  const { className, icon } = getBadgeProps();

  return (
    <Badge className={`gap-1 font-mono uppercase text-[10px] ${className}`}>
      {icon}
      <span>{status.replace(/_/g, ' ')}</span>
    </Badge>
  );
};

export const PriorityBadge: React.FC<{ priority: PriorityLevel | string }> = ({ priority }) => {
  const getStyle = () => {
    switch (priority) {
      case 'CRITICAL':
        return 'bg-rose-50 text-rose-800 border-rose-200';
      case 'HIGH':
        return 'bg-amber-50 text-amber-800 border-amber-200';
      case 'MEDIUM':
        return 'bg-slate-100 text-slate-700 border-slate-200';
      default:
        return 'bg-slate-100 text-slate-600 border-slate-200';
    }
  };

  return (
    <Badge className={`font-mono text-[10px] uppercase ${getStyle()}`}>
      {priority}
    </Badge>
  );
};

