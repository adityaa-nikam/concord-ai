'use client';

import React, { useEffect, useState } from 'react';
import { Metrics } from '@/components/Metrics';
import { CaseTable } from '@/components/CaseTable';
import { fetchCases, fetchDemoHealth } from '@/lib/api';
import { CaseListResponse } from '@/lib/types';
import { RefreshCw, Database, Server, Cpu, ShieldCheck, Zap } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DashboardPage() {
  const [data, setData] = useState<CaseListResponse | null>(null);
  const [health, setHealth] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    setLoading(true);
    try {
      const [casesRes, healthRes] = await Promise.all([
        fetchCases(),
        fetchDemoHealth().catch(() => null)
      ]);
      setData(casesRes);
      setHealth(healthRes);
    } catch (e) {
      console.error("Failed to load dashboard data", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  return (
    <div className="space-y-6 font-sans">
      
      {/* Editorial Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Payment Exceptions
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Resolve ambiguous payment states across transaction ledgers and payment gateways.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={loadData}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </Button>
        </div>
      </div>

      {/* Single Operational Summary Line */}
      <Metrics
        total={data?.total || 0}
        active={data?.active_cases_count || 0}
        escalated={data?.escalated_count || 0}
        resolved={data?.resolved_count || 0}
      />

      {/* Large Data Table */}
      <div className="space-y-2">
        <div className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider font-sans">
          Active Dispute Queue
        </div>
        <CaseTable cases={data?.cases || []} onRefresh={loadData} />
      </div>

      {/* System Status Footer */}
      <div className="bg-white border border-slate-200 rounded-md p-3.5">
        <div className="flex items-center justify-between mb-3 border-b border-slate-100 pb-2">
          <span className="text-[11px] font-semibold text-slate-700 uppercase tracking-wider font-sans">System Status & Infrastructure</span>
          <span className="text-[11px] font-mono text-slate-500">
            LLM ENGINE: <strong className="text-slate-900">{health?.llm_mode || 'MOCK'}</strong>
          </span>
        </div>
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3 text-xs font-sans">
          <div className="bg-slate-50/70 p-2.5 rounded border border-slate-200/80 space-y-0.5">
            <div className="text-[10px] text-slate-500 uppercase flex items-center gap-1 font-medium">
              <Database className="w-3 h-3 text-slate-400" /> Database
            </div>
            <div className="text-emerald-700 font-semibold font-mono text-[11px]">Healthy</div>
          </div>

          <div className="bg-slate-50/70 p-2.5 rounded border border-slate-200/80 space-y-0.5">
            <div className="text-[10px] text-slate-500 uppercase flex items-center gap-1 font-medium">
              <Server className="w-3 h-3 text-slate-400" /> API Gateway
            </div>
            <div className="text-emerald-700 font-semibold font-mono text-[11px]">Active</div>
          </div>

          <div className="bg-slate-50/70 p-2.5 rounded border border-slate-200/80 space-y-0.5">
            <div className="text-[10px] text-slate-500 uppercase flex items-center gap-1 font-medium">
              <Cpu className="w-3 h-3 text-slate-400" /> LangGraph Agent
            </div>
            <div className="text-emerald-700 font-semibold font-mono text-[11px]">Ready</div>
          </div>

          <div className="bg-slate-50/70 p-2.5 rounded border border-slate-200/80 space-y-0.5">
            <div className="text-[10px] text-slate-500 uppercase flex items-center gap-1 font-medium">
              <ShieldCheck className="w-3 h-3 text-slate-400" /> Policy Gate
            </div>
            <div className="text-emerald-700 font-semibold font-mono text-[11px]">Enforced</div>
          </div>

          <div className="bg-slate-50/70 p-2.5 rounded border border-slate-200/80 space-y-0.5">
            <div className="text-[10px] text-slate-500 uppercase flex items-center gap-1 font-medium">
              <Zap className="w-3 h-3 text-slate-400" /> Action Gateway
            </div>
            <div className="text-emerald-700 font-semibold font-mono text-[11px]">Available</div>
          </div>
        </div>
      </div>

    </div>
  );
}

