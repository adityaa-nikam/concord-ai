import React from 'react';
import { CheckCircle2, Clock, Wrench, ShieldCheck, AlertCircle, Cpu } from 'lucide-react';
import { AgentRun, AuditLog } from '@/lib/types';

interface AgentTimelineProps {
  agentRuns: AgentRun[];
  auditLogs: AuditLog[];
  currentStatus: string;
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ agentRuns, auditLogs, currentStatus }) => {
  const latestRun = agentRuns.length > 0 ? agentRuns[agentRuns.length - 1] : null;

  const nodes = [
    { key: 'intake', label: 'Customer Intake' },
    { key: 'investigation', label: 'Diagnostics' },
    { key: 'ai_evidence_interpretation', label: 'AI Assessment' },
    { key: 'policy_check', label: 'Policy Check' },
    { key: 'ai_resolution_proposal', label: 'Resolution Proposal' },
    { key: 'decision', label: 'Policy Gate' },
    { key: 'action', label: 'Action & Verification' },
  ];

  const getStepStatus = (index: number) => {
    if (currentStatus === 'RESOLVED') return 'completed';
    if (currentStatus === 'ESCALATED') return index <= 3 ? 'completed' : 'escalated';
    if (!latestRun) return index === 0 ? 'active' : 'pending';
    const completed = latestRun.steps_completed;
    if (index < completed) return 'completed';
    if (index === completed) return 'active';
    return 'pending';
  };

  const getActorBadge = (actor: string) => {
    const act = (actor || 'SYSTEM').toUpperCase();
    if (act.includes('AI') || act.includes('LLM')) {
      return <span className="px-1.5 py-0.5 rounded bg-slate-100 text-slate-800 font-mono text-[10px] font-medium border border-slate-200">AI</span>;
    }
    if (act.includes('POLICY') || act.includes('GATE')) {
      return <span className="px-1.5 py-0.5 rounded bg-emerald-50 text-emerald-800 font-mono text-[10px] font-medium border border-emerald-200">POLICY GATE</span>;
    }
    if (act.includes('HUMAN') || act.includes('OPS')) {
      return <span className="px-1.5 py-0.5 rounded bg-rose-50 text-rose-800 font-mono text-[10px] font-medium border border-rose-200">HUMAN OPS</span>;
    }
    return <span className="px-1.5 py-0.5 rounded bg-slate-50 text-slate-600 font-mono text-[10px] font-medium border border-slate-200">SYSTEM</span>;
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* Node Workflow Pipeline Stepper */}
      <div className="bg-white border border-slate-200 rounded-md p-4 space-y-3 font-sans">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono flex items-center gap-2">
          <Cpu className="w-4 h-4 text-slate-700" />
          LangGraph Execution Pipeline Node Sequence
        </h3>

        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2">
          {nodes.map((n, idx) => {
            const st = getStepStatus(idx);
            return (
              <div
                key={n.key}
                className={`p-2.5 rounded border text-xs flex flex-col justify-between transition-all font-mono ${
                  st === 'completed'
                    ? 'bg-emerald-50 border-emerald-200 text-emerald-900'
                    : st === 'active'
                    ? 'bg-amber-50 border-amber-300 text-amber-900 font-semibold'
                    : st === 'escalated'
                    ? 'bg-rose-50 border-rose-200 text-rose-900'
                    : 'bg-slate-50 border-slate-200 text-slate-400'
                }`}
              >
                <div className="font-semibold text-[11px] truncate">{n.label}</div>
                <div className="mt-2 text-[10px] uppercase font-mono flex items-center justify-between">
                  <span>{st}</span>
                  {st === 'completed' && <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />}
                  {st === 'active' && <Clock className="w-3.5 h-3.5 text-amber-600 animate-spin" />}
                  {st === 'escalated' && <AlertCircle className="w-3.5 h-3.5 text-rose-600" />}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Tool Invocations Telemetry Log */}
      <div className="bg-white border border-slate-200 rounded-md p-4 space-y-3 font-sans">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono flex items-center gap-2">
          <Wrench className="w-4 h-4 text-slate-700" />
          Tool Invocations & Microservice Telemetry
        </h3>

        {!latestRun || latestRun.tool_calls.length === 0 ? (
          <div className="p-6 text-center text-slate-400 text-xs font-mono bg-slate-50 rounded border border-slate-200">
            No agent tool calls recorded for this case yet. Click "Run Agent" to trigger execution.
          </div>
        ) : (
          <div className="space-y-3 font-mono">
            {latestRun.tool_calls.map((tc, i) => (
              <div key={tc.id || i} className="bg-slate-50 border border-slate-200 rounded-md p-3.5 space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <span className="bg-white text-slate-900 px-2 py-0.5 rounded text-xs font-mono font-bold border border-slate-200">
                      {tc.tool_name}
                    </span>
                    <span className="text-xs text-slate-500 font-mono">
                      {new Date(tc.created_at).toLocaleTimeString()}
                    </span>
                  </div>
                  <span className="text-xs font-semibold text-emerald-700 flex items-center gap-1 font-sans">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    {tc.status}
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs font-mono pt-1">
                  {/* Input Payload */}
                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <div className="text-slate-500 font-bold mb-1 text-[10px] uppercase font-sans">Input Arguments</div>
                    <pre className="text-slate-800 text-[11px] overflow-x-auto">
                      {JSON.stringify(tc.input_payload, null, 2)}
                    </pre>
                  </div>

                  {/* Output Payload */}
                  <div className="bg-white p-2.5 rounded border border-slate-200">
                    <div className="text-slate-500 font-bold mb-1 text-[10px] uppercase font-sans">Tool Output Payload</div>
                    <pre className="text-slate-900 text-[11px] overflow-x-auto">
                      {JSON.stringify(tc.output_payload, null, 2)}
                    </pre>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Immutable Audit Log Stream */}
      <div className="bg-white border border-slate-200 rounded-md p-4 space-y-3 font-sans">
        <h3 className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono flex items-center gap-2">
          <ShieldCheck className="w-4 h-4 text-emerald-600" />
          Immutable Case Execution Audit Trail
        </h3>

        <div className="relative border-l border-slate-200 ml-3 space-y-4 py-2 font-mono text-xs">
          {auditLogs.length === 0 ? (
            <p className="text-xs text-slate-400 pl-4 font-mono">No audit logs recorded for this case yet.</p>
          ) : (
            auditLogs.map((log, index) => (
              <div key={log.id || index} className="relative pl-6 space-y-1">
                <div className="absolute -left-1.5 top-1.5 w-3 h-3 rounded-full bg-slate-400 border-2 border-white"></div>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="font-bold text-slate-900">{log.event_type}</span>
                    {getActorBadge(log.actor)}
                  </div>
                  <span className="text-[11px] text-slate-400 font-mono">
                    {new Date(log.created_at).toLocaleTimeString()}
                  </span>
                </div>
                {log.details && (
                  <pre className="mt-1 text-[11px] font-mono text-slate-700 bg-slate-50 p-2.5 rounded border border-slate-200 overflow-x-auto">
                    {JSON.stringify(log.details, null, 2)}
                  </pre>
                )}
              </div>
            ))
          )}
        </div>
      </div>

    </div>
  );
};

