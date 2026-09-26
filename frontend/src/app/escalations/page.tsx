'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { fetchEscalations, triggerReversal } from '@/lib/api';
import { CaseDetail } from '@/lib/types';
import { StatusBadge, PriorityBadge } from '@/components/StatusBadge';
import {
  RefreshCw, Lock, ExternalLink, ShieldAlert, CheckCircle2, ChevronRight, ChevronDown, AlertTriangle
} from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function EscalationsPage() {
  const [escalations, setEscalations] = useState<CaseDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionRunning, setActionRunning] = useState<string | null>(null);
  const [expandedCaseId, setExpandedCaseId] = useState<string | null>(null);

  const loadEscalations = async () => {
    setLoading(true);
    try {
      const data = await fetchEscalations();
      setEscalations(data);
      if (data.length > 0 && !expandedCaseId) {
        setExpandedCaseId(data[0].id);
      }
    } catch (e) {
      console.error("Failed to load escalations", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEscalations();
  }, []);

  const handleManualReversal = async (c: CaseDetail) => {
    const confirm = window.confirm(`Override AI decision and trigger manual reversal of ₹${c.transaction?.amount} for Case ${c.case_number}?`);
    if (!confirm) return;
    setActionRunning(c.id);
    try {
      await triggerReversal(c.id, c.transaction.id, "Tier 2 Human Ops Manual Override");
      await loadEscalations();
    } catch (err: any) {
      alert(`Manual reversal failed: ${err.message}`);
    } finally {
      setActionRunning(null);
    }
  };

  return (
    <div className="space-y-6 font-sans max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Human Operations Queue
            </h1>
            <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-amber-50 text-amber-800 border border-amber-200 font-medium">
              Tier 2 Handoff
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Dispute cases flagged for human analyst review due to policy thresholds, verification failures, or manual override requirements.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <Button
            variant="outline"
            size="sm"
            onClick={loadEscalations}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            Refresh Queue
          </Button>
        </div>
      </div>

      {/* Queue Body */}
      {loading ? (
        <div className="py-16 text-center text-slate-500 text-xs font-sans">
          <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
          Loading Tier 2 human operations queue...
        </div>
      ) : escalations.length === 0 ? (
        <div className="bg-white border border-slate-200 rounded-md p-8 text-center text-slate-500 space-y-2">
          <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
          <h3 className="text-sm font-semibold text-slate-900">No Pending Human Escalations</h3>
          <p className="text-xs text-slate-500 max-w-md mx-auto">
            All UPI dispute cases are currently being processed autonomously within standard policy limits.
          </p>
          <div className="pt-2">
            <Link
              href="/cases"
              className="inline-block bg-slate-900 text-white hover:bg-slate-800 text-xs font-medium px-3.5 py-1.5 rounded transition-colors"
            >
              View Payment Exceptions
            </Link>
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          
          {/* Distinct Escalation Warning Banner */}
          <div className="bg-rose-50 border border-rose-200 rounded-md p-4 text-xs font-sans space-y-1">
            <div className="flex items-center gap-2 text-rose-800 font-bold uppercase tracking-wider text-[11px]">
              <AlertTriangle className="w-4 h-4 text-rose-600" />
              Escalated Cases Awaiting Analyst Authorization
            </div>
            <p className="text-slate-700">
              The autonomous teammate encountered cases where verification failed or policy thresholds required human sign-off.
            </p>
          </div>

          {/* Table of Escalated Cases */}
          <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 text-[10px] font-semibold">
                  <tr>
                    <th className="py-2.5 px-4">Case ID</th>
                    <th className="py-2.5 px-4">Customer</th>
                    <th className="py-2.5 px-4">Escalation Reason</th>
                    <th className="py-2.5 px-4 text-right">Amount</th>
                    <th className="py-2.5 px-4">Priority</th>
                    <th className="py-2.5 px-4">Status</th>
                    <th className="py-2.5 px-4 text-right">Handoff Packet</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {escalations.map((item) => {
                    const isExpanded = expandedCaseId === item.id;
                    return (
                      <React.Fragment key={item.id}>
                        <tr
                          onClick={() => setExpandedCaseId(isExpanded ? null : item.id)}
                          className={`cursor-pointer transition-colors ${
                            isExpanded ? 'bg-slate-50/90' : 'hover:bg-slate-50/50'
                          }`}
                        >
                          <td className="py-3 px-4 font-mono font-semibold text-slate-900 flex items-center gap-1.5">
                            {isExpanded ? (
                              <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                            ) : (
                              <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                            )}
                            {item.case_number}
                          </td>
                          <td className="py-3 px-4 text-slate-900 font-medium">
                            {item.customer?.name}
                          </td>
                          <td className="py-3 px-4 text-slate-600 max-w-xs truncate">
                            {item.issue_description}
                          </td>
                          <td className="py-3 px-4 text-right font-mono font-semibold text-slate-900">
                            ₹{item.transaction?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                          </td>
                          <td className="py-3 px-4">
                            <PriorityBadge priority={item.priority} />
                          </td>
                          <td className="py-3 px-4">
                            <StatusBadge status={item.status} />
                          </td>
                          <td className="py-3 px-4 text-right">
                            <span className="text-[11px] font-medium text-slate-900 hover:underline">
                              {isExpanded ? 'Close Packet' : 'Inspect Handoff'}
                            </span>
                          </td>
                        </tr>

                        {/* Detailed Escalation Handoff Packet */}
                        {isExpanded && (
                          <tr className="bg-slate-50/80">
                            <td colSpan={7} className="p-6 border-b border-slate-200 font-sans">
                              <div className="max-w-4xl space-y-5 bg-white border border-slate-200 rounded-md p-6">
                                
                                {/* Handoff Header */}
                                <div className="flex items-center justify-between border-b border-slate-200 pb-3">
                                  <div>
                                    <div className="flex items-center gap-2">
                                      <span className="text-xs font-bold text-rose-700 tracking-wider uppercase font-mono">
                                        ESCALATION REQUIRED
                                      </span>
                                      <span className="text-slate-300">•</span>
                                      <span className="font-mono text-sm font-bold text-slate-900">
                                        {item.case_number}
                                      </span>
                                    </div>
                                    <p className="text-xs text-slate-600 mt-1">
                                      Automated resolution halted. Autonomous agent requires analyst authorization prior to ledger override.
                                    </p>
                                  </div>

                                  <div className="text-right">
                                    <span className="text-[10px] text-slate-400 font-mono uppercase block">Dispute Amount</span>
                                    <span className="text-xl font-bold font-mono text-slate-900">
                                      ₹{item.transaction?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}
                                    </span>
                                  </div>
                                </div>

                                {/* Escalation Reason Section */}
                                <div className="space-y-1">
                                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                                    Escalation Trigger Reason
                                  </span>
                                  <p className="text-sm font-medium text-slate-900 leading-snug">
                                    &quot;{item.issue_description}&quot;
                                  </p>
                                </div>

                                <div className="h-px bg-slate-100"></div>

                                {/* Observed Evidence Signals Table */}
                                <div className="space-y-2">
                                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                                    Observed Evidence Telemetry
                                  </span>
                                  <div className="grid grid-cols-3 gap-4 font-mono text-xs bg-slate-50 p-3 rounded border border-slate-100">
                                    <div>
                                      <span className="text-slate-500 font-sans block text-[11px]">Remitter Ledger</span>
                                      <span className="font-semibold text-slate-900">{item.transaction?.remitter_debit_status || 'ON_HOLD'}</span>
                                    </div>
                                    <div>
                                      <span className="text-slate-500 font-sans block text-[11px]">Beneficiary Bank</span>
                                      <span className="font-semibold text-rose-700">{item.transaction?.beneficiary_credit_status || 'NOT_CREDITED'}</span>
                                    </div>
                                    <div>
                                      <span className="text-slate-500 font-sans block text-[11px]">NPCI Switch</span>
                                      <span className="font-semibold text-slate-900">{item.transaction?.npci_status || 'UNKNOWN'}</span>
                                    </div>
                                  </div>
                                </div>

                                <div className="h-px bg-slate-100"></div>

                                {/* Recommended Action & Override Bar */}
                                <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-1">
                                  <div>
                                    <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold block">
                                      Recommended Operations Action
                                    </span>
                                    <p className="text-xs text-slate-700 mt-0.5">
                                      Review settlement log state before triggering manual reversal override.
                                    </p>
                                  </div>

                                  <div className="flex items-center gap-3 shrink-0">
                                    <Link
                                      href={`/cases/${item.id}`}
                                      className="text-xs font-semibold text-slate-700 hover:text-slate-900 border border-slate-200 bg-white hover:bg-slate-50 px-3 py-1.5 rounded transition-colors flex items-center gap-1 font-sans"
                                    >
                                      Review Full Case <ExternalLink className="w-3 h-3" />
                                    </Link>

                                    <Button
                                      onClick={(e) => {
                                        e.stopPropagation();
                                        handleManualReversal(item);
                                      }}
                                      disabled={actionRunning === item.id}
                                      size="sm"
                                      className="bg-slate-900 hover:bg-slate-800 text-white text-xs px-4 py-1.5 rounded transition-colors disabled:opacity-50 font-sans font-medium"
                                    >
                                      {actionRunning === item.id ? 'Executing Reversal...' : 'Authorize Manual Reversal'}
                                    </Button>
                                  </div>
                                </div>

                              </div>
                            </td>
                          </tr>
                        )}
                      </React.Fragment>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}



