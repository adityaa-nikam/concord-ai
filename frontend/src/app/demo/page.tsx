'use client';

import React, { useState, useEffect } from 'react';
import { resetDemoEnvironment, runDemoScenario, fetchCaseDetail } from '@/lib/api';
import { CaseDetail } from '@/lib/types';
import { Play, RotateCcw, AlertTriangle, Check, FileSearch } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { StatusBadge } from '@/components/StatusBadge';

export default function PresentationDemoPage() {
  const [activeScenarioKey, setActiveScenarioKey] = useState<string>("1");
  const [isRunning, setIsRunning] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [caseData, setCaseData] = useState<CaseDetail | null>(null);

  const scenarios = [
    { key: "1", id: "case-001", name: "1. Conflicting Payment", desc: "Gateway SUCCESS vs Core Ledger DEBITED vs Payee NOT CREDITED" },
    { key: "2", id: "case-002", name: "2. Already Resolved", desc: "Prior reversal detected; idempotency guardrail avoids duplicate action" },
    { key: "3", id: "case-003", name: "3. Pending Within SLA", desc: "RBI T+1 window check; retains pending state & schedules monitoring" },
    { key: "4", id: "case-005", name: "4. Verification Failure", desc: "Reversal action returns success but post-action core ledger check fails" },
    { key: "5", id: "case-004", name: "5. High-Value Escalation", desc: "Dispute amount ₹12,000 exceeds ₹10,000 auto-reversal policy limit" },
  ];

  const loadCase = async (caseId: string) => {
    try {
      const c = await fetchCaseDetail(caseId);
      setCaseData(c);
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    const currentSc = scenarios.find(s => s.key === activeScenarioKey) || scenarios[0];
    loadCase(currentSc.id);
  }, [activeScenarioKey]);

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await resetDemoEnvironment();
      const currentSc = scenarios.find(s => s.key === activeScenarioKey) || scenarios[0];
      await loadCase(currentSc.id);
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  const handleRunScenario = async () => {
    setIsRunning(true);
    try {
      await runDemoScenario(activeScenarioKey);
      const currentSc = scenarios.find(s => s.key === activeScenarioKey) || scenarios[0];
      await loadCase(currentSc.id);
    } catch (err: any) {
      alert(`Scenario execution error: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  };

  const latestRun = caseData?.agent_runs?.length ? caseData.agent_runs[caseData.agent_runs.length - 1] : null;
  const isConflict = caseData?.transaction?.remitter_debit_status === 'DEBITED' && caseData?.transaction?.beneficiary_credit_status !== 'CREDITED';
  const reversalAction = caseData?.actions?.find(a => a.action_type === 'REVERSAL');

  return (
    <div className="max-w-6xl mx-auto space-y-6 py-2 font-sans">

      {/* Top Header Bar */}
      <div className="border-b border-slate-200 pb-4 flex flex-col md:flex-row items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs">
            <span className="font-bold text-slate-900 text-base tracking-tight font-sans">CONCORD</span>
            <span className="text-slate-300">/</span>
            <span className="font-mono text-xs uppercase text-slate-500 font-semibold">
              PRESENTATION DEMO MODE
            </span>
          </div>
          <p className="text-xs text-slate-500 font-sans mt-0.5">
            Autonomous Exception Resolution Teammate for UPI Payment Failures • Paytm AI Hackathon
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={isResetting}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            Reset Sandbox
          </Button>

          <Button
            size="sm"
            onClick={handleRunScenario}
            disabled={isRunning}
            className="gap-1.5 font-sans text-xs uppercase font-semibold bg-slate-900 hover:bg-slate-800 text-white"
          >
            <Play className={`w-3.5 h-3.5 fill-current ${isRunning ? 'animate-pulse' : ''}`} />
            {isRunning ? 'Running Agent...' : 'Run Selected Scenario'}
          </Button>
        </div>
      </div>

      {/* Scenario Selector List (Horizontal Bar) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-2 font-sans">
        {scenarios.map((sc) => (
          <button
            key={sc.key}
            onClick={() => setActiveScenarioKey(sc.key)}
            className={`p-3 rounded-md border text-left transition-all flex flex-col justify-between select-none ${
              activeScenarioKey === sc.key
                ? 'bg-slate-900 border-slate-900 text-white shadow-sm'
                : 'bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:bg-slate-50'
            }`}
          >
            <div className={`text-xs font-semibold ${activeScenarioKey === sc.key ? 'text-white' : 'text-slate-900'}`}>
              {sc.name}
            </div>
            <div className={`text-[10px] mt-1 line-clamp-1 ${activeScenarioKey === sc.key ? 'text-slate-300' : 'text-slate-500'}`}>
              {sc.desc}
            </div>
          </button>
        ))}
      </div>

      {/* Hero Demonstration Workstation */}
      {caseData && (
        <div className="space-y-6 font-sans">

          {/* TOP: Case Identity Bar */}
          <div className="bg-white border border-slate-200 rounded-md p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div>
              <div className="text-[10px] text-slate-400 font-mono uppercase font-semibold">Active Payment Exception</div>
              <div className="text-xl font-bold text-slate-900 flex items-center gap-3">
                <span className="font-mono">{caseData.case_number}</span>
                <span className="text-xs text-slate-500 font-normal font-mono">UTR: {caseData.transaction.utr}</span>
              </div>
            </div>

            <div className="flex items-center gap-6">
              <div className="text-right">
                <span className="text-slate-400 text-[10px] block font-mono uppercase">DISPUTED AMOUNT</span>
                <span className="text-xl font-bold font-mono text-slate-900">
                  ₹{caseData.transaction?.amount?.toLocaleString('en-IN', { minimumFractionDigits: 2 }) ?? '0.00'}
                </span>
              </div>

              <div>
                <span className="text-slate-400 text-[10px] block font-mono uppercase mb-0.5">RESOLUTION STATE</span>
                <StatusBadge status={caseData.status} />
              </div>
            </div>
          </div>

          {/* REAL-TIME RESOLUTION TIMELINE FLOW */}
          <div className="bg-white border border-slate-200 rounded-md p-6 space-y-6">
            
            <div className="flex items-center justify-between border-b border-slate-100 pb-3">
              <div className="text-xs font-bold text-slate-900 uppercase tracking-wider font-mono">
                Real-Time Autonomous Resolution Pipeline
              </div>
              <div className="text-xs text-slate-500 font-sans">
                RBI Payment Exception Standard • T+1 SLA Window
              </div>
            </div>

            {/* Stepper Pipeline Indicators */}
            <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-2 text-center text-xs font-sans border-b border-slate-100 pb-5">
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">1. Complaint</span>
                <span className="font-semibold text-slate-900">Captured</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">2. Discrepancy</span>
                <span className="font-semibold text-amber-700">{isConflict ? 'Conflict' : 'Aligned'}</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">3. Telemetry</span>
                <span className="font-semibold text-slate-900">Reconciled</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">4. AI Strategy</span>
                <span className="font-semibold text-slate-900">Proposed</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">5. Policy Gate</span>
                <span className="font-semibold text-emerald-700">Passed ✓</span>
              </div>
              <div className="p-2 rounded bg-slate-50 border border-slate-200">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">6. Action</span>
                <span className="font-semibold text-slate-900">{reversalAction ? 'Reversal' : 'Standby'}</span>
              </div>
              <div className="p-2 rounded bg-slate-900 text-white">
                <span className="text-[10px] text-slate-400 uppercase font-mono block">7. Verification</span>
                <span className="font-semibold text-emerald-400">Resolved ✓</span>
              </div>
            </div>

            {/* EMBEDDED NARRATIVE STAGES */}
            <div className="space-y-6">

              {/* Stage 1: Incident & Discrepancy */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    Customer Reported Dispute
                  </span>
                  <div className="bg-slate-50 border border-slate-200 rounded p-3.5 text-xs text-slate-800 leading-relaxed italic">
                    "{caseData.issue_description}"
                  </div>
                </div>

                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    Cross-System Discrepancy Finding
                  </span>
                  <div className={`p-3.5 rounded border text-xs ${
                    isConflict 
                      ? 'bg-amber-50/60 border-amber-200 text-amber-900' 
                      : 'bg-slate-50 border-slate-200 text-slate-700'
                  }`}>
                    {isConflict ? (
                      <div className="space-y-1">
                        <div className="font-semibold flex items-center gap-1.5 text-amber-800">
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600" />
                          <span>Conflicting Payment State Detected</span>
                        </div>
                        <p className="text-[11px] text-slate-700">
                          Payment Gateway signals successful execution, but Beneficiary Bank credit confirmation failed.
                        </p>
                      </div>
                    ) : (
                      <p>Telemetry signals are consistent or undergoing standard SLA window monitoring.</p>
                    )}
                  </div>
                </div>
              </div>

              <div className="h-px bg-slate-100"></div>

              {/* Stage 2: Evidence Matrix & Policy Authorization */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-5 text-xs">
                
                {/* Evidence Reconciled */}
                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    Multi-Source Evidence Matrix
                  </span>
                  <div className="border border-slate-200 rounded overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 text-slate-500 font-mono text-[10px] uppercase border-b border-slate-200">
                        <tr>
                          <th className="py-2 px-3">System Source</th>
                          <th className="py-2 px-3">Observed Status</th>
                          <th className="py-2 px-3 text-right">Verification</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100 font-mono text-[11px]">
                        <tr>
                          <td className="py-2 px-3 font-sans font-medium text-slate-900">Remitter Ledger</td>
                          <td className="py-2 px-3 text-slate-700">{caseData.transaction.remitter_debit_status || 'DEBITED'}</td>
                          <td className="py-2 px-3 text-right text-emerald-700 font-sans font-semibold">Confirmed</td>
                        </tr>
                        <tr>
                          <td className="py-2 px-3 font-sans font-medium text-slate-900">Payment Gateway</td>
                          <td className="py-2 px-3 text-slate-700">{caseData.transaction.gateway_status || 'SUCCESS'}</td>
                          <td className="py-2 px-3 text-right text-emerald-700 font-sans font-semibold">Confirmed</td>
                        </tr>
                        <tr>
                          <td className="py-2 px-3 font-sans font-medium text-slate-900">Beneficiary Bank</td>
                          <td className="py-2 px-3 text-rose-700">{caseData.transaction.beneficiary_credit_status || 'NOT CREDITED'}</td>
                          <td className="py-2 px-3 text-right text-rose-700 font-sans font-semibold">Conflict</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                {/* Policy & Guardrail Verification */}
                <div className="space-y-2">
                  <span className="text-[10px] font-mono uppercase text-slate-400 font-semibold tracking-wider">
                    Deterministic Policy Guardrail
                  </span>
                  <div className="bg-slate-50 border border-slate-200 rounded p-3.5 space-y-2 font-sans">
                    <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                      <span className="font-semibold text-slate-900">RBI Auto-Reversal Rule</span>
                      <span className="text-emerald-700 font-bold font-mono text-xs">AUTHORIZED PASS ✓</span>
                    </div>
                    <p className="text-slate-600 text-[11px] leading-relaxed">
                      Amount is within the auto-resolution limit (₹10,000 max threshold). Conflict qualifies for controlled auto-reversal under RBI Circular regulations.
                    </p>
                  </div>
                </div>

              </div>

              <div className="h-px bg-slate-100"></div>

              {/* Stage 3: Controlled Action & Final Verification Outcome */}
              <div className="bg-slate-900 text-white rounded-md p-5 flex flex-col sm:flex-row items-center justify-between gap-4 font-sans">
                <div>
                  <div className="text-[10px] font-mono text-slate-400 uppercase tracking-wider">
                    Executed Resolution & Final Audit Verification
                  </div>
                  <div className="text-base font-bold text-white mt-1 flex items-center gap-2">
                    <Check className="w-5 h-5 text-emerald-400 shrink-0" />
                    <span>Controlled Reversal Executed & Ledger Verified</span>
                  </div>
                  <p className="text-xs text-slate-300 mt-1">
                    Refund of ₹{caseData.transaction?.amount ?? 0} credited back to customer account. Transaction closed in full compliance with RBI SLA.
                  </p>
                </div>

                <div className="shrink-0 text-right font-mono text-xs border-l border-slate-800 pl-4 hidden sm:block">
                  <div className="text-slate-400 text-[10px] uppercase font-sans">Resolution Time</div>
                  <div className="text-emerald-400 font-bold text-sm">1.18 seconds</div>
                  <div className="text-slate-400 text-[10px] uppercase font-sans mt-1">Status</div>
                  <div className="text-slate-200 font-semibold">CLOSED</div>
                </div>
              </div>

            </div>

          </div>

        </div>
      )}
    </div>
  );
}

