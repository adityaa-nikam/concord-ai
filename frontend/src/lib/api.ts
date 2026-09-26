import { CaseListResponse, CaseDetail, AgentRun, AuditLog } from './types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export async function fetchCases(status?: string, search?: string): Promise<CaseListResponse> {
  const params = new URLSearchParams();
  if (status) params.append('status', status);
  if (search) params.append('search', search);

  try {
    const res = await fetch(`${API_BASE}/api/cases?${params.toString()}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn("Backend API unavailable, using fallback seed view", error);
    return getFallbackCases();
  }
}

export async function fetchCaseDetail(caseId: string): Promise<CaseDetail> {
  try {
    const res = await fetch(`${API_BASE}/api/cases/${caseId}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn(`Backend API unavailable for case ${caseId}, using fallback`, error);
    return getFallbackCaseDetail(caseId);
  }
}

export async function triggerAgentRun(caseId: string): Promise<AgentRun> {
  const res = await fetch(`${API_BASE}/api/agent/run/${caseId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Failed to run agent');
  }
  return await res.json();
}

export async function fetchAgentRuns(): Promise<AgentRun[]> {
  try {
    const res = await fetch(`${API_BASE}/api/agent/runs`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn("Backend API unavailable for agent runs", error);
    return [];
  }
}

export async function fetchAgentRunDetail(runId: string): Promise<AgentRun> {
  const res = await fetch(`${API_BASE}/api/agent/runs/${runId}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return await res.json();
}

export async function fetchAuditLogs(caseId?: string): Promise<AuditLog[]> {
  try {
    const params = new URLSearchParams();
    if (caseId) params.append('case_id', caseId);
    const res = await fetch(`${API_BASE}/api/audit?${params.toString()}`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn("Backend API unavailable for audit logs", error);
    return [];
  }
}

export async function fetchEscalations(): Promise<CaseDetail[]> {
  try {
    const res = await fetch(`${API_BASE}/api/escalations`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    console.warn("Backend API unavailable for escalations", error);
    return [];
  }
}

export async function triggerReversal(caseId: string, transactionId: string, reason: string) {
  const res = await fetch(`${API_BASE}/api/actions/reversal`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      case_id: caseId,
      transaction_id: transactionId,
      reason,
      initiated_by: 'MANUAL_OPS_OVERRIDE',
    }),
  });
  if (!res.ok) throw new Error('Reversal trigger failed');
  return await res.json();
}

export async function triggerEscalation(caseId: string, reason: string) {
  const res = await fetch(`${API_BASE}/api/cases/${caseId}/escalate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ case_id: caseId, reason }),
  });
  if (!res.ok) throw new Error('Escalation trigger failed');
  return await res.json();
}

export async function fetchDemoHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/demo/health`, { cache: 'no-store' });
    if (!res.ok) throw new Error(`API error: ${res.status}`);
    return await res.json();
  } catch (error) {
    return { status: 'STANDALONE_DEMO', components: { database: 'MOCK', agent_graph: 'READY' } };
  }
}

export async function resetDemoEnvironment() {
  const res = await fetch(`${API_BASE}/api/demo/reset`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to reset demo environment');
  return await res.json();
}

export async function runDemoScenario(scenarioId: string) {
  const res = await fetch(`${API_BASE}/api/demo/scenario/${scenarioId}/run`, { method: 'POST' });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || 'Demo scenario execution failed');
  }
  return await res.json();
}

// Fallback seed data for standalone offline preview
function getFallbackCases(): CaseListResponse {
  return {
    total: 4,
    active_cases_count: 3,
    escalated_count: 1,
    resolved_count: 1,
    cases: [
      {
        id: "case-001",
        case_number: "CAS-2026-0001",
        status: "NEW",
        priority: "HIGH",
        issue_description: "₹2,400 was deducted from my account, but the merchant/receiver did not receive the money.",
        customer_name: "Rajesh Kumar",
        customer_upi: "rajesh@paytm",
        transaction_utr: "426189012345",
        amount: 2400.0,
        tat_deadline: new Date(Date.now() + 22 * 3600 * 1000).toISOString(),
        created_at: new Date().toISOString()
      },
      {
        id: "case-002",
        case_number: "CAS-2026-0002",
        status: "RESOLVED",
        priority: "MEDIUM",
        issue_description: "Money deducted for Swiggy order, did not reach merchant.",
        customer_name: "Priya Sharma",
        customer_upi: "priya@upi",
        transaction_utr: "426189098765",
        amount: 1500.0,
        tat_deadline: new Date(Date.now() + 18 * 3600 * 1000).toISOString(),
        created_at: new Date().toISOString()
      },
      {
        id: "case-003",
        case_number: "CAS-2026-0003",
        status: "NEW",
        priority: "CRITICAL",
        issue_description: "Large transfer of ₹12,000 stuck in pending state for over 4 hours.",
        customer_name: "Amit Patel",
        customer_upi: "amit@paytm",
        transaction_utr: "426189555666",
        amount: 12000.0,
        tat_deadline: new Date(Date.now() + 14 * 3600 * 1000).toISOString(),
        created_at: new Date().toISOString()
      },
      {
        id: "case-004",
        case_number: "CAS-2026-0004",
        status: "NEW",
        priority: "LOW",
        issue_description: "Paid for groceries 2 mins ago, seller says money not received.",
        customer_name: "Sneha Reddy",
        customer_upi: "sneha@axis",
        transaction_utr: "426189777888",
        amount: 500.0,
        tat_deadline: new Date(Date.now() + 23 * 3600 * 1000).toISOString(),
        created_at: new Date().toISOString()
      }
    ]
  };
}

function getFallbackCaseDetail(caseId: string): CaseDetail {
  return {
    id: caseId,
    case_number: caseId === "case-003" ? "CAS-2026-0003" : "CAS-2026-0001",
    status: caseId === "case-003" ? "ESCALATED" : "NEW",
    priority: "HIGH",
    issue_description: "₹2,400 was deducted from my account, but the merchant/receiver did not receive the money.",
    tat_deadline: new Date(Date.now() + 22 * 3600 * 1000).toISOString(),
    resolution_summary: undefined,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    customer: {
      id: "cust-001",
      name: "Rajesh Kumar",
      phone: "+91 9876543210",
      email: "rajesh.kumar@example.com",
      upi_id: "rajesh@paytm",
      created_at: new Date().toISOString()
    },
    transaction: {
      id: "tx-001",
      utr: "426189012345",
      amount: 2400.0,
      payer_upi: "rajesh@paytm",
      payee_upi: "merchant@paytm",
      status: "PENDING",
      failure_reason: "NPCI_SWITCH_TIMEOUT",
      remitter_bank: "Paytm Payments Bank",
      beneficiary_bank: "State Bank of India",
      remitter_debit_status: "DEBITED",
      beneficiary_credit_status: "NOT_CREDITED",
      gateway_status: "SUCCESS",
      npci_status: "TIMEOUT",
      created_at: new Date().toISOString()
    },
    agent_runs: [],
    actions: [],
    audit_logs: [
      {
        id: "aud-001",
        case_id: caseId,
        event_type: "CASE_CREATED",
        actor: "SYSTEM",
        details: { source: "CUSTOMER_DISPUTE_PORTAL" },
        created_at: new Date().toISOString()
      }
    ]
  };
}
