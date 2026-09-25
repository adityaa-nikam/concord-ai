'use client';

import React, { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { fetchDemoHealth, resetDemoEnvironment, runDemoScenario } from '@/lib/api';
import { Play, RefreshCw, CheckCircle2, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

export default function DemoScenariosPage() {
  const router = useRouter();
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [isResetting, setIsResetting] = useState(false);
  const [healthInfo, setHealthInfo] = useState<any>(null);
  const [executionResult, setExecutionResult] = useState<any>(null);

  useEffect(() => {
    loadHealth();
  }, []);

  const loadHealth = async () => {
    const data = await fetchDemoHealth();
    setHealthInfo(data);
  };

  const handleReset = async () => {
    setIsResetting(true);
    try {
      await resetDemoEnvironment();
      await loadHealth();
      setExecutionResult(null);
      alert('Demo sandbox environment reset to baseline!');
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setIsResetting(false);
    }
  };

  const scenarios = [
    {
      key: "1",
      id: "case-001",
      case_number: "CAS-2026-0001",
      title: "Conflicting Telemetry Exception",
      purpose: "Cross-System Signal Reconciliation",
      customer: "Rajesh Kumar (rajesh@paytm)",
      amount: "₹2,400.00",
      utr: "426189012345",
      complaint: "₹2,400 deducted, beneficiary not credited.",
      tat: "T+1",
      expectedOutcome: "Idempotent Reversal & Post-Action Verification",
    },
    {
      key: "2",
      id: "case-002",
      case_number: "CAS-2026-0002",
      title: "Already Reversed Guardrail",
      purpose: "Duplicate Action Protection",
      customer: "Priya Sharma (priya@upi)",
      amount: "₹1,500.00",
      utr: "426189098765",
      complaint: "Swiggy order payment stuck.",
      tat: "T+1",
      expectedOutcome: "Detect Prior Reversal → Avoid Duplicate Action → Close Case",
    },
    {
      key: "3",
      id: "case-003",
      case_number: "CAS-2026-0003",
      title: "Pending Within RBI Window",
      purpose: "SLA TAT Evaluation & Monitoring",
      customer: "Sneha Reddy (sneha@axis)",
      amount: "₹500.00",
      utr: "426189777888",
      complaint: "Paid groceries 2m ago, uncredited.",
      tat: "T+1",
      expectedOutcome: "RBI T+1 Window Valid → Retain Pending State → Schedule Polling",
    },
    {
      key: "4",
      id: "case-005",
      case_number: "CAS-2026-0005",
      title: "Post-Verification Failure",
      purpose: "Human Escalation Handoff",
      customer: "Vikram Singh (vikram@paytm)",
      amount: "₹3,500.00",
      utr: "426189999000",
      complaint: "Electronics purchase deducted, seller uncredited.",
      tat: "T+1",
      expectedOutcome: "Reversal API Success → Core Ledger Locked → Escalate to Human Ops",
    },
    {
      key: "5",
      id: "case-004",
      case_number: "CAS-2026-0004",
      title: "High-Value Policy Limit",
      purpose: "Policy Threshold Enforcement",
      customer: "Amit Patel (amit@paytm)",
      amount: "₹12,000.00",
      utr: "426189555666",
      complaint: "Large transfer of ₹12,000 stuck over 4 hours.",
      tat: "T+1",
      expectedOutcome: "Exceeds ₹10k Auto-Threshold → Policy Gate Deny → Tier 2 Escalation",
    }
  ];

  const handleRunScenario = async (sc: any) => {
    setRunningScenario(sc.key);
    try {
      const res = await runDemoScenario(sc.key);
      setExecutionResult(res);
      setTimeout(() => {
        router.push(`/cases/${sc.id}`);
      }, 1000);
    } catch (err: any) {
      alert(`Scenario execution error: ${err.message}`);
    } finally {
      setRunningScenario(null);
    }
  };

  return (
    <div className="space-y-6 font-sans max-w-6xl mx-auto">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-xl font-bold text-slate-900 tracking-tight">
              Policy Rules & Scenarios
            </h1>
            <span className="text-[10px] font-sans px-2 py-0.5 rounded bg-slate-100 text-slate-700 border border-slate-200 font-medium">
              Deterministic Guardrails
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-0.5">
            Pre-configured payment dispute scenarios to validate policy checks, idempotency, TAT engine, and escalation thresholds.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="sm"
            onClick={handleReset}
            disabled={isResetting}
            className="gap-1.5 text-slate-700 bg-white border-slate-200 hover:bg-slate-50 text-xs"
          >
            <RotateCcw className={`w-3.5 h-3.5 ${isResetting ? 'animate-spin' : ''}`} />
            Reset Sandbox State
          </Button>
        </div>
      </div>

      {/* Execution Results Notification Banner */}
      {executionResult && (
        <div className="bg-slate-900 text-white rounded-md p-4 space-y-2 text-xs font-sans">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400">
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              Scenario Executed: <span className="text-white font-mono">{executionResult.scenario?.name}</span>
            </div>
            <span className="font-mono text-xs text-slate-400">
              Duration: <strong className="text-white">{executionResult.duration_ms} ms</strong>
            </span>
          </div>
          <div className="text-xs text-slate-300 grid grid-cols-2 md:grid-cols-4 gap-2 font-mono">
            <div>Final State: <span className="font-semibold text-emerald-400">{executionResult.final_case_status}</span></div>
            <div>Steps Completed: <span className="font-semibold text-white">{executionResult.steps_completed}</span></div>
            <div>Tools Invoked: <span className="font-semibold text-slate-200">{executionResult.tool_calls_count}</span></div>
            <div>Run ID: <span className="text-slate-400">{executionResult.run_id?.slice(0, 8)}...</span></div>
          </div>
        </div>
      )}

      {/* Scenario Table Matrix */}
      <div className="bg-white border border-slate-200 rounded-md overflow-hidden font-sans">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 uppercase tracking-wider border-b border-slate-200 text-[10px] font-semibold">
              <tr>
                <th className="py-2.5 px-4">Policy Scenario</th>
                <th className="py-2.5 px-4">TAT Rule</th>
                <th className="py-2.5 px-4">Dispute Amount</th>
                <th className="py-2.5 px-4">Expected Autonomous Outcome</th>
                <th className="py-2.5 px-4 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 bg-white">
              {scenarios.map((sc) => (
                <tr key={sc.key} className="hover:bg-slate-50/70 transition-colors font-sans">
                  <td className="py-3 px-4">
                    <div className="font-bold text-slate-900">{sc.title}</div>
                    <div className="font-mono text-[11px] text-slate-500 mt-0.5">{sc.case_number} · {sc.purpose}</div>
                  </td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                    {sc.tat}
                  </td>
                  <td className="py-3 px-4 font-mono font-semibold text-slate-900">
                    {sc.amount}
                  </td>
                  <td className="py-3 px-4 text-slate-700 max-w-sm text-xs">
                    {sc.expectedOutcome}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <Button
                      onClick={() => handleRunScenario(sc)}
                      disabled={runningScenario === sc.key}
                      size="sm"
                      className="gap-1.5 font-sans text-xs bg-slate-900 hover:bg-slate-800 text-white"
                    >
                      {runningScenario === sc.key ? (
                        <>
                          <RefreshCw className="w-3 h-3 animate-spin" />
                          Executing...
                        </>
                      ) : (
                        <>
                          <Play className="w-3 h-3 fill-current" />
                          Run Scenario
                        </>
                      )}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

    </div>
  );
}



