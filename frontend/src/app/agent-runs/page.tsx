'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchAgentRuns } from '@/lib/api';
import { AgentRun } from '@/lib/types';
import { RefreshCw, CheckCircle2, AlertCircle, Clock, ExternalLink } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AgentRunsPage() {
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRuns = async () => {
    setLoading(true);
    try {
      const data = await fetchAgentRuns();
      setRuns(data);
    } catch (e) {
      console.error("Failed to load agent runs", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  return (
    <div className="space-y-6 font-sans max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Agent Execution Traces
            </h1>
            <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
              LangGraph Engine
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Developer observability log for autonomous dispute resolution node execution and tool invocations.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadRuns}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Traces
          </Button>
        </div>
      </div>

      {/* Runs Table */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
            Fetching agent execution traces...
          </div>
        ) : runs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs font-sans">
            No agent runs recorded yet. Execute a dispute case from the Payment Exceptions queue.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Run ID</th>
                  <th className="py-2.5 px-4">Case Target</th>
                  <th className="py-2.5 px-4">Status</th>
                  <th className="py-2.5 px-4">Node Steps</th>
                  <th className="py-2.5 px-4">Tools Invoked</th>
                  <th className="py-2.5 px-4">Started At</th>
                  <th className="py-2.5 px-4 text-right">Trace Log</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {runs.map((r) => (
                  <tr key={r.id} className="hover:bg-slate-50/70 transition-colors font-sans">
                    <td className="py-3 px-4 font-mono font-semibold text-slate-900 text-xs">
                      {r.id.substring(0, 16)}...
                    </td>

                    <td className="py-3 px-4">
                      <Link href={`/cases/${r.case_id}`} className="font-mono text-slate-900 hover:underline text-xs inline-flex items-center gap-1 font-semibold">
                        {r.case_id} <ExternalLink className="w-3 h-3 text-slate-400" />
                      </Link>
                    </td>

                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-sans font-medium inline-flex items-center gap-1 ${
                        r.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' :
                        r.status === 'RUNNING' ? 'bg-amber-50 text-amber-800 border border-amber-200' :
                        'bg-rose-50 text-rose-800 border border-rose-200'
                      }`}>
                        {r.status === 'COMPLETED' && <CheckCircle2 className="w-3 h-3 text-emerald-600" />}
                        {r.status === 'RUNNING' && <Clock className="w-3 h-3 text-amber-600 animate-spin" />}
                        {r.status === 'FAILED' && <AlertCircle className="w-3 h-3 text-rose-600" />}
                        {r.status}
                      </span>
                    </td>

                    <td className="py-3 px-4 font-mono text-xs text-slate-700">
                      {r.steps_completed} steps
                    </td>

                    <td className="py-3 px-4 font-mono text-xs text-slate-700">
                      {r.tool_calls?.length || 0} tools
                    </td>

                    <td className="py-3 px-4 font-mono text-xs text-slate-500">
                      {new Date(r.started_at).toLocaleTimeString()}
                    </td>

                    <td className="py-3 px-4 text-right">
                      <Link
                        href={`/agent-runs/${r.id}`}
                        className="inline-flex items-center gap-1 bg-white hover:bg-slate-50 text-slate-900 border border-slate-200 text-xs font-semibold px-2.5 py-1 rounded transition-colors font-sans"
                      >
                        Inspect Trace
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}



