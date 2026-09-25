'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchAuditLogs } from '@/lib/api';
import { AuditLog } from '@/lib/types';
import { RefreshCw, Search, ExternalLink, ChevronRight, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function AuditTrailPage() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const data = await fetchAuditLogs();
      setLogs(data);
    } catch (e) {
      console.error("Failed to load audit logs", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAuditLogs();
  }, []);

  const filteredLogs = logs.filter((log) => {
    if (!search) return true;
    const query = search.toLowerCase();
    return (
      log.event_type.toLowerCase().includes(query) ||
      log.actor.toLowerCase().includes(query) ||
      log.case_id.toLowerCase().includes(query)
    );
  });

  const getActorBadge = (actor: string) => {
    const act = actor.toUpperCase();
    if (act.includes('AI') || act.includes('AGENT')) {
      return (
        <span className="bg-slate-100 text-slate-800 border border-slate-200 px-1.5 py-0.5 rounded text-[10px] font-sans font-medium">
          Concord-AI
        </span>
      );
    }
    if (act.includes('HUMAN') || act.includes('OPS')) {
      return (
        <span className="bg-amber-50 text-amber-800 border border-amber-200 px-1.5 py-0.5 rounded text-[10px] font-sans font-medium">
          Human Ops
        </span>
      );
    }
    return (
      <span className="bg-slate-50 text-slate-600 border border-slate-200 px-1.5 py-0.5 rounded text-[10px] font-sans font-medium">
        System
      </span>
    );
  };

  return (
    <div className="space-y-6 font-sans max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Immutable Audit Trail
            </h1>
            <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
              Financial Control Ledger
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Cryptographically verifiable audit log recording evidence interpretations, policy gate checks, and action executions.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadAuditLogs}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Stream
          </Button>
        </div>
      </div>

      {/* Audit Log Table */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
        
        {/* Search Bar */}
        <div className="p-3 border-b border-slate-200 bg-slate-50/50">
          <div className="relative w-full sm:w-80">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              placeholder="Filter Event, Actor, or Case ID..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-white border border-slate-200 text-slate-900 text-xs rounded pl-8 pr-3 py-1.5 focus:outline-none focus:border-slate-400 placeholder-slate-400 font-sans"
            />
          </div>
        </div>

        {/* Audit List */}
        {loading ? (
          <div className="py-16 text-center text-slate-500 text-xs">
            <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
            Fetching immutable audit ledger...
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="py-12 text-center text-slate-500 text-xs font-sans">
            No audit records match your search query.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 text-[10px] font-semibold">
                <tr>
                  <th className="py-2.5 px-4">Event</th>
                  <th className="py-2.5 px-4">Actor</th>
                  <th className="py-2.5 px-4">Case Target</th>
                  <th className="py-2.5 px-4">Timestamp</th>
                  <th className="py-2.5 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {filteredLogs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  return (
                    <React.Fragment key={log.id}>
                      <tr
                        onClick={() => setExpandedLogId(isExpanded ? null : log.id)}
                        className={`cursor-pointer transition-colors ${
                          isExpanded ? 'bg-slate-50/80' : 'hover:bg-slate-50/50'
                        }`}
                      >
                        <td className="py-3 px-4 font-mono font-semibold text-slate-900 flex items-center gap-1.5">
                          {isExpanded ? (
                            <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                          ) : (
                            <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                          )}
                          {log.event_type}
                        </td>
                        <td className="py-3 px-4">
                          {getActorBadge(log.actor)}
                        </td>
                        <td className="py-3 px-4 font-mono text-xs">
                          <Link href={`/cases/${log.case_id}`} className="text-slate-900 hover:underline font-semibold inline-flex items-center gap-1">
                            {log.case_id} <ExternalLink className="w-3 h-3 text-slate-400" />
                          </Link>
                        </td>
                        <td className="py-3 px-4 font-mono text-xs text-slate-500">
                          {new Date(log.created_at).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <span className="text-[11px] font-sans font-medium text-slate-900 hover:underline">
                            {isExpanded ? 'Hide Payload' : 'Inspect'}
                          </span>
                        </td>
                      </tr>

                      {isExpanded && log.details && (
                        <tr className="bg-slate-50/60">
                          <td colSpan={5} className="p-3 border-b border-slate-200">
                            <div className="text-[10px] font-semibold text-slate-500 uppercase tracking-wider mb-1 font-sans">
                              Audit Event Payload State
                            </div>
                            <pre className="bg-white p-3 rounded border border-slate-200 text-slate-800 font-mono text-[11px] overflow-x-auto">
                              {JSON.stringify(log.details, null, 2)}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
}



