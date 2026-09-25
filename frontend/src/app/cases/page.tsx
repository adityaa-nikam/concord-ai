'use client';

import React, { useEffect, useState } from 'react';
import { fetchCases } from '@/lib/api';
import { CaseListResponse } from '@/lib/types';
import { CaseTable } from '@/components/CaseTable';
import { Metrics } from '@/components/Metrics';
import { RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function CasesQueuePage() {
  const [data, setData] = useState<CaseListResponse | null>(null);
  const [loading, setLoading] = useState(true);

  const loadCases = async () => {
    setLoading(true);
    try {
      const res = await fetchCases();
      setData(res);
    } catch (e) {
      console.error("Failed to fetch cases", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCases();
  }, []);

  return (
    <div className="space-y-6 font-sans">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-900 tracking-tight">
            Payment Exceptions
          </h1>
          <p className="text-xs text-slate-500 mt-0.5">
            Active UPI exception cases monitored by Concord for RBI TAT compliance and automated resolution.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadCases}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </Button>
        </div>
      </div>

      {/* Operational Summary */}
      <Metrics
        total={data?.total || 0}
        active={data?.active_cases_count || 0}
        escalated={data?.escalated_count || 0}
        resolved={data?.resolved_count || 0}
      />

      {/* Main Case Table */}
      <CaseTable cases={data?.cases || []} onRefresh={loadCases} />
    </div>
  );
}


