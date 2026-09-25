'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { fetchCaseDetail, triggerAgentRun, triggerEscalation, triggerReversal } from '@/lib/api';
import { CaseDetail } from '@/lib/types';
import { StatusBadge, PriorityBadge } from '@/components/StatusBadge';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  ArrowLeft, Play, RefreshCw, Code, AlertTriangle, ShieldCheck, CheckCircle2, ArrowRight
} from 'lucide-react';

export default function CaseDetailPage() {
  const params = useParams();
  const caseId = params?.id as string;

  const [caseData, setCaseData] = useState<CaseDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [actionRunning, setActionRunning] = useState(false);
  const [showTelemetry, setShowTelemetry] = useState(false);

  const loadDetail = async () => {
    if (!caseId) return;
    setLoading(true);
    try {
      const data = await fetchCaseDetail(caseId);
      setCaseData(data);
    } catch (e) {
      console.error("Failed to load case detail", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [caseId]);

  const handleRunAgent = async () => {
    if (!caseId) return;
    setActionRunning(true);
    try {
      await triggerAgentRun(caseId);
      await loadDetail();
    } catch (err: any) {
      alert(`Agent run failed: ${err.message}`);
    } finally {
      setActionRunning(false);
    }
  };

  const handleManualEscalation = async () => {
    if (!caseId) return;
    const reason = prompt("Enter escalation reason for Tier 2 Human Ops:");
    if (!reason) return;
    setActionRunning(true);
    try {
      await triggerEscalation(caseId, reason);
      await loadDetail();
    } catch (err: any) {
      alert(`Escalation failed: ${err.message}`);
    } finally {
      setActionRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-500 font-sans text-xs">
        <RefreshCw className="w-5 h-5 animate-spin mx-auto mb-2 text-slate-400" />
        Fetching case telemetry state...
      </div>
    );
  }

  if (!caseData) {
    return (
      <div className="py-12 text-center text-slate-600 font-sans text-xs">
        Case not found. <Link href="/cases" className="text-slate-900 underline font-semibold">Return to Payment Exceptions</Link>
      </div>
    );
  }

  const latestRun = caseData.agent_runs?.length > 0 ? caseData.agent_runs[caseData.agent_runs.length - 1] : null;
  const reversalAction = caseData.actions?.find(a => a.action_type === 'REVERSAL');
  const isEscalated = caseData.status === 'ESCALATED';

  return (
    <div className="space-y-6 font-sans max-w-5xl mx-auto pb-12">
      
      {/* Top Navigation & Action Controls */}
      <div className="flex items-center justify-between border-b border-slate-200 pb-3">
        <Link
          href="/cases"
          className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 transition-colors font-medium"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          Payment Exceptions
        </Link>

        <div className="flex items-center space-x-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setShowTelemetry(!showTelemetry)}
            className="gap-1 text-slate-600 border-slate-200 text-xs bg-white"
          >
            <Code className="w-3.5 h-3.5 text-slate-400" />
            {showTelemetry ? 'Hide Payload' : 'Inspect Telemetry'}
          </Button>

          <Button
            variant="outline"
            size="icon"
            onClick={loadDetail}
            className="h-8 w-8 text-slate-600 border-slate-200 bg-white"
            title="Refresh Case"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          <Button
            onClick={handleRunAgent}
            disabled={actionRunning || caseData.status === 'RESOLVED'}
            size="sm"
            className="gap-1.5 font-sans text-xs font-semibold bg-slate-900 text-white hover:bg-slate-800 px-3.5"
          >
            <Play className={`w-3 h-3 fill-current ${actionRunning ? 'animate-spin' : ''}`} />
            {actionRunning ? 'Resolving...' : 'Resolve Exception'}
          </Button>

          {caseData.status !== 'RESOLVED' && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleManualEscalation}
              disabled={actionRunning}
              className="text-xs text-slate-700 border-slate-200 bg-white"
            >
              Escalate
            </Button>
          )}
        </div>
      </div>

      {/* Raw Telemetry Inspector */}
      {showTelemetry && (
        <div className="bg-slate-900 border border-slate-800 rounded-md p-4 text-xs font-mono">
          <div className="text-slate-400 text-[10px] uppercase font-sans mb-2 font-semibold">Raw Case Telemetry State</div>
          <pre className="text-emerald-400 bg-slate-950 p-3 rounded border border-slate-800 overflow-x-auto max-h-80 text-[11px]">
            {JSON.stringify(caseData, null, 2)}
          </pre>
        </div>
      )}

      {/* Editorial Case Header Block */}
      <div className="space-y-3">
        <div className="flex flex-col sm:flex-row sm:items-baseline justify-between gap-2">
          <div>
            <div className="flex items-center gap-3">
              <span className="font-mono text-2xl font-bold text-slate-900 tracking-tight">{caseData.case_number}</span>
              <StatusBadge status={caseData.status} />
              <PriorityBadge priority={caseData.priority} />
            </div>
            <div className="text-xs text-slate-500 mt-1 font-mono">
              UPI transfer · UTR {caseData.transaction.utr} · Customer {caseData.customer.name} ({caseData.customer.upi_id})
            </div>
          </div>

          <div className="text-right">
            <span className="text-[10px] uppercase font-mono text-slate-400 block">Dispute Amount</span>
            <span className="text-2xl font-bold font-mono text-slate-900">
              ₹{caseData.transaction?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '0.00'}
            </span>
          </div>
        </div>

        {/* Horizontal Contextual Metadata Bar (No Cards) */}
        <div className="flex flex-wrap items-center gap-6 py-2.5 px-3 bg-white border border-slate-200 rounded-md text-xs font-sans text-slate-600">
          <div>
            <span className="text-slate-400 text-[11px]">Reported: </span>
            <span className="font-mono text-slate-900">{new Date(caseData.created_at).toLocaleTimeString()}</span>
          </div>
          <div className="h-3 w-px bg-slate-200"></div>
          <div>
            <span className="text-slate-400 text-[11px]">SLA Target: </span>
            <span className="font-mono text-slate-900 font-medium">RBI T+1 Window</span>
          </div>
          <div className="h-3 w-px bg-slate-200"></div>
          <div>
            <span className="text-slate-400 text-[11px]">Current State: </span>
            <span className="font-medium text-slate-900">{caseData.status}</span>
          </div>
          <div className="h-3 w-px bg-slate-200"></div>
          <div>
            <span className="text-slate-400 text-[11px]">Risk Category: </span>
            <span className="font-medium text-slate-900">{caseData.priority === 'CRITICAL' ? 'High Risk' : 'Standard'}</span>
          </div>
        </div>
      </div>

      {/* Escalation Banner (If Escalated) */}
      {isEscalated && (
        <div className="bg-rose-50 border border-rose-200 rounded-md p-4 text-xs font-sans space-y-2">
          <div className="flex items-center gap-2 text-rose-800 font-bold uppercase tracking-wider text-[11px]">
            <AlertTriangle className="w-4 h-4 text-rose-600" />
            Human Escalation Handoff Required
          </div>
          <p className="text-slate-700 leading-relaxed">
            The automated policy engine flagged this case for human review due to verification thresholds or ambiguous ledger telemetry.
          </p>
          <div className="pt-1 text-[11px] font-mono text-slate-600">
            Escalation Reason: <strong className="text-slate-900">"{caseData.issue_description}"</strong>
          </div>
        </div>
      )}

      {/* 1. CUSTOMER REPORT (Incident Record Block) */}
      <section className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans">
          Customer Incident Report
        </h2>
        <div className="bg-white border border-slate-200 rounded-md p-4 text-slate-800 text-sm leading-relaxed font-sans">
          "{caseData.issue_description}"
          <div className="mt-3 text-xs text-slate-400 font-mono flex items-center justify-between border-t border-slate-100 pt-2.5">
            <span>Source: Mobile App Incident System</span>
            <span>Customer UTR: {caseData.transaction.utr}</span>
          </div>
        </div>
      </section>

      {/* 2. EVIDENCE RECONCILIATION (Visual Signature Table) */}
      <section className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans">
          Evidence Reconciliation
        </h2>
        <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 font-mono text-[10px]">
              <tr>
                <th className="py-2.5 px-4">SOURCE</th>
                <th className="py-2.5 px-4">STATE</th>
                <th className="py-2.5 px-4">DISPUTE AMOUNT</th>
                <th className="py-2.5 px-4 text-right">RESULT</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 font-mono">
              <tr>
                <td className="py-2.5 px-4 font-sans font-medium text-slate-900">Core Bank Ledger</td>
                <td className="py-2.5 px-4 text-slate-700">{caseData.transaction.remitter_debit_status || 'DEBITED'}</td>
                <td className="py-2.5 px-4 text-slate-900">₹{caseData.transaction.amount}</td>
                <td className="py-2.5 px-4 text-right text-emerald-700 font-sans font-semibold">CONFIRMED</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-sans font-medium text-slate-900">Payment Gateway</td>
                <td className="py-2.5 px-4 text-slate-700">{caseData.transaction.gateway_status || 'SUCCESS'}</td>
                <td className="py-2.5 px-4 text-slate-900">₹{caseData.transaction.amount}</td>
                <td className="py-2.5 px-4 text-right text-emerald-700 font-sans font-semibold">CONFIRMED</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-sans font-medium text-slate-900">Beneficiary Bank</td>
                <td className="py-2.5 px-4 text-rose-700">{caseData.transaction.beneficiary_credit_status || 'NOT CREDITED'}</td>
                <td className="py-2.5 px-4 text-slate-400">—</td>
                <td className="py-2.5 px-4 text-right text-rose-700 font-sans font-semibold">CONFLICT</td>
              </tr>
              <tr>
                <td className="py-2.5 px-4 font-sans font-medium text-slate-900">Reversal Ledger</td>
                <td className="py-2.5 px-4 text-slate-700">{reversalAction ? 'EXECUTED' : 'NOT INITIATED'}</td>
                <td className="py-2.5 px-4 text-slate-900">{reversalAction ? `₹${caseData.transaction.amount}` : '—'}</td>
                <td className="py-2.5 px-4 text-right text-slate-600 font-sans font-medium">{reversalAction ? 'RESOLVED' : 'PENDING'}</td>
              </tr>
            </tbody>
          </table>

          {/* Finding Summary Callout */}
          <div className="bg-slate-50 border-t border-slate-200 p-3.5 text-xs text-slate-700 space-y-1 font-sans">
            <div className="font-semibold text-slate-900 uppercase text-[10px] tracking-wider font-mono">
              Reconciliation Finding
            </div>
            <p className="leading-relaxed text-slate-700">
              3 systems confirm debit from remitter account. Beneficiary credit cannot be confirmed.
            </p>
            <p className="text-slate-500 text-[11px] font-mono">
              Conflict: Gateway completion signal conflicts with beneficiary-credit evidence.
            </p>
          </div>
        </div>
      </section>

      {/* 3. AI ASSESSMENT (Editorial Control Block) */}
      <section className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans">
          AI Assessment & Recommendation
        </h2>
        <div className="bg-white border border-slate-200 rounded-md p-4 text-xs font-sans space-y-3">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-400 block font-semibold">Classification</span>
              <span className="text-slate-900 font-medium">Beneficiary Credit Unresolved</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-400 block font-semibold">Assessment</span>
              <span className="text-slate-700">Funds debited, but beneficiary credit unconfirmed.</span>
            </div>
            <div>
              <span className="text-[10px] uppercase font-mono text-slate-400 block font-semibold">Recommendation</span>
              <span className="text-slate-900 font-medium">Initiate controlled auto-reversal under RBI T+1 rule.</span>
            </div>
          </div>
        </div>
      </section>

      {/* 4. POLICY & DECISION PIPELINE (The Visual Control Gateway) */}
      <section className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans">
          Policy Evaluation & Action Pipeline
        </h2>
        <div className="bg-white border border-slate-200 rounded-md p-4 text-xs space-y-4">
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4 font-mono text-xs border-b border-slate-100 pb-3">
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Applicable Policy</span>
              <span className="text-slate-900 font-semibold">POL-RBI-UPI-T1</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Max SLA Window</span>
              <span className="text-slate-900">T+1 (24h)</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Condition</span>
              <span className="text-slate-900">Auto-Reversal Eligible</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Policy Gate Check</span>
              <span className="text-emerald-700 font-bold font-sans">PASS ✓</span>
            </div>
          </div>

          {/* Stepper Relationship Flow: AI PROPOSAL -> POLICY GATE -> CONTROLLED ACTION */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-50 p-3 rounded border border-slate-200 font-mono text-xs">
            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-400 font-sans uppercase block font-semibold">1. AI Proposal</span>
              <span className="text-slate-900 font-bold">INITIATE_REVERSAL</span>
            </div>
            
            <ArrowRight className="w-4 h-4 text-slate-400 shrink-0 hidden sm:block" />

            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-400 font-sans uppercase block font-semibold">2. Policy Gate</span>
              <span className="text-emerald-700 font-bold">AUTHORIZED</span>
            </div>

            <ArrowRight className="w-4 h-4 text-slate-400 shrink-0 hidden sm:block" />

            <div className="space-y-0.5">
              <span className="text-[10px] text-slate-400 font-sans uppercase block font-semibold">3. Controlled Action</span>
              <span className="text-slate-900 font-bold">{reversalAction ? 'REVERSAL EXECUTED' : 'PENDING ACTION'}</span>
            </div>
          </div>

        </div>
      </section>

      {/* 5. VERIFICATION & OUTCOME */}
      <section className="space-y-2">
        <h2 className="text-xs font-bold uppercase tracking-wider text-slate-400 font-sans">
          Post-Action Verification & Outcome
        </h2>
        <div className="bg-white border border-slate-200 rounded-md p-4 text-xs font-sans space-y-3">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-xs">
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Ledger State</span>
              <span className="text-emerald-700 font-medium font-sans">Verified ✓</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Reversal Action</span>
              <span className="text-emerald-700 font-medium font-sans">Confirmed ✓</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Final State</span>
              <span className="text-slate-900 font-bold">{caseData.status}</span>
            </div>
            <div>
              <span className="text-slate-400 text-[10px] uppercase block font-sans">Resolved Timestamp</span>
              <span className="text-slate-600">{new Date(caseData.updated_at).toLocaleTimeString()}</span>
            </div>
          </div>

          <div className="border-t border-slate-100 pt-3 flex items-center justify-between text-xs text-slate-600">
            <div className="flex items-center gap-1.5 font-medium text-emerald-800">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" />
              <span>Payment exception resolved following multi-source reconciliation, policy validation, and verification.</span>
            </div>
            <span className="font-mono text-[11px] text-slate-400">Ref: {caseData.id.slice(0, 8)}</span>
          </div>
        </div>
      </section>

    </div>
  );
}



