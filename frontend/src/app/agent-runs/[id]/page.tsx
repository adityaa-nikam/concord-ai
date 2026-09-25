'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { fetchAgentRunDetail } from '@/lib/api';
import { AgentRun } from '@/lib/types';
import {
  ArrowLeft, CheckCircle2, RefreshCw, ChevronDown, ChevronRight
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AgentRunTracePage() {
  const params = useParams();
  const runId = params?.id as string;

  const [runData, setRunData] = useState<AgentRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  const loadRun = async () => {
    if (!runId) return;
    setLoading(true);
    try {
      const data = await fetchAgentRunDetail(runId);
      setRunData(data);
    } catch (e) {
      console.error("Failed to load run detail", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadRun();
  }, [runId]);

  if (loading) {
    return (
      <div className="py-16 text-center text-slate-500 text-xs font-sans">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
        Loading agent execution trace log...
      </div>
    );
  }

  if (!runData) {
    return (
      <div className="py-12 text-center text-slate-600 font-sans text-xs">
        Run ID not found. <Link href="/agent-runs" className="text-slate-900 underline font-semibold">Return to Agent Observability</Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 font-sans max-w-5xl mx-auto pb-12">
      
      {/* Navigation Header */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-4">
        <div className="flex items-center gap-3">
          <Link
            href="/agent-runs"
            className="inline-flex items-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Agent Traces
          </Link>
          <span className="text-slate-300">/</span>
          <span className="font-mono text-xs font-semibold text-slate-900">
            {runData.id}
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={loadRun}
          className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Refresh
        </Button>
      </div>

      {/* Main Run Summary Block */}
      <div className="bg-white border border-slate-200 rounded-md p-4 space-y-3 font-sans">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-100 pb-3">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-bold text-slate-900 font-sans">Execution Trace Log</span>
              <span className={`px-2 py-0.5 rounded text-[10px] font-sans font-medium ${
                runData.status === 'COMPLETED' ? 'bg-emerald-50 text-emerald-800 border border-emerald-200' : 'bg-rose-50 text-rose-800 border border-rose-200'
              }`}>
                {runData.status}
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1 font-sans">
              Target Case: <Link href={`/cases/${runData.case_id}`} className="text-slate-900 hover:underline font-mono font-semibold">{runData.case_id}</Link>
            </p>
          </div>

          <div className="flex items-center space-x-6 text-xs text-slate-600">
            <div>
              <span className="text-slate-400 font-sans">Node Steps:</span> <span className="text-slate-900 font-mono font-semibold">{runData.steps_completed}</span>
            </div>
            <div>
              <span className="text-slate-400 font-sans font-medium">Tools Invoked:</span> <span className="text-slate-900 font-mono font-semibold">{runData.tool_calls?.length || 0}</span>
            </div>
            <div>
              <span className="text-slate-400 font-sans">Timestamp:</span> <span className="text-slate-900 font-mono">{new Date(runData.started_at).toLocaleTimeString()}</span>
            </div>
          </div>
        </div>

        {/* Error message if present */}
        {runData.error_message && (
          <div className="bg-rose-50 border border-rose-200 p-3 rounded text-rose-800 text-xs font-mono">
            <strong>Execution Error:</strong> {runData.error_message}
          </div>
        )}
      </div>

      {/* Tool Call Step Invocations */}
      <div className="bg-white border border-slate-200 rounded-md p-4 space-y-3 font-sans">
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider font-sans">
          Tool Invocation Traces
        </h3>

        {!runData.tool_calls || runData.tool_calls.length === 0 ? (
          <p className="text-xs text-slate-500 font-sans">No tool calls logged for this run.</p>
        ) : (
          <div className="divide-y divide-slate-100 border border-slate-200 rounded overflow-hidden">
            {runData.tool_calls.map((tc, index) => {
              const isExpanded = expandedIndex === index;
              return (
                <div key={tc.id || index} className="bg-white">
                  <div
                    onClick={() => setExpandedIndex(isExpanded ? null : index)}
                    className="p-3 flex items-center justify-between cursor-pointer hover:bg-slate-50/80 transition-colors"
                  >
                    <div className="flex items-center space-x-3">
                      {isExpanded ? (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                      )}
                      <span className="text-xs font-mono font-semibold text-slate-900">
                        0{index + 1} {tc.tool_name}
                      </span>
                      <span className="text-[11px] font-mono text-slate-400">
                        ({new Date(tc.created_at).toLocaleTimeString()})
                      </span>
                    </div>

                    <div className="flex items-center space-x-3">
                      <span className="text-[11px] font-sans text-emerald-700 font-medium inline-flex items-center gap-1">
                        <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                        {tc.status}
                      </span>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="p-3 bg-slate-50 border-t border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
                      <div>
                        <div className="text-slate-500 uppercase text-[10px] font-semibold mb-1 font-sans">Input Arguments</div>
                        <pre className="bg-white p-2.5 rounded border border-slate-200 text-slate-800 overflow-x-auto text-[11px]">
                          {JSON.stringify(tc.input_payload, null, 2)}
                        </pre>
                      </div>
                      <div>
                        <div className="text-slate-500 uppercase text-[10px] font-semibold mb-1 font-sans">Output Payload</div>
                        <pre className="bg-white p-2.5 rounded border border-slate-200 text-slate-900 overflow-x-auto text-[11px]">
                          {JSON.stringify(tc.output_payload, null, 2)}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

    </div>
  );
}


