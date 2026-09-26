export type CaseStatus =
  | 'NEW'
  | 'INVESTIGATING'
  | 'POLICY_CHECK'
  | 'ACTION_REQUIRED'
  | 'ACTION_IN_PROGRESS'
  | 'VERIFYING'
  | 'RESOLVED'
  | 'ESCALATED'
  | 'FAILED';

export type PriorityLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface Customer {
  id: string;
  name: string;
  phone: string;
  email?: string;
  upi_id: string;
  created_at: string;
}

export interface Transaction {
  id: string;
  utr: string;
  amount: number;
  payer_upi: string;
  payee_upi: string;
  status: string;
  failure_reason?: string;
  remitter_bank: string;
  beneficiary_bank: string;
  remitter_debit_status: string;
  beneficiary_credit_status: string;
  gateway_status: string;
  npci_status: string;
  created_at: string;
}

export interface ToolCall {
  id: string;
  tool_name: string;
  input_payload?: any;
  output_payload?: any;
  status: string;
  created_at: string;
}

export interface NormalizedEvidenceItem {
  source: string;
  field: string;
  value: any;
  observed_at: string;
  reliability: 'SYSTEM_OF_RECORD' | 'SECONDARY_DERIVED' | 'UNVERIFIED_CUSTOMER_CLAIM';
  freshness: 'CURRENT' | 'STALE' | 'HISTORICAL';
  notes?: string;
}

export interface PolicyMatch {
  policy_id: string;

  title: string;
  clause_reference: string;
  summary: string;
  rule_condition: string;
  permitted_actions: string[];
  prohibited_actions: string[];
  auto_execution_allowed: boolean;
  min_confidence_required: number;
  max_amount_limit?: number;
  relevance_score: number;
}

export interface ReasoningSummary {
  facts_grounding: string;
  policy_grounding: string;
  safety_and_idempotency: string;
}

export interface ResolutionAssessment {
  decision: string;
  proposed_action: string;
  reasoning_summary: ReasoningSummary;
  confidence_score: number;
  requires_human_override: boolean;
  policy_id_triggered: string;
  idempotency_key?: string;
  reason_code: string;
}

export interface AgentRun {
  id: string;
  case_id: string;
  status: string;
  steps_completed: number;
  started_at: string;
  completed_at?: string;
  error_message?: string;
  tool_calls: ToolCall[];
  normalized_evidence?: NormalizedEvidenceItem[];
  reconciliation_report?: any;
  retrieved_policies?: PolicyMatch[];
  resolution_assessment?: ResolutionAssessment;
  state_snapshot?: any;
}

export interface Action {
  id: string;
  case_id: string;
  action_type: string;
  status: string;
  initiated_by: string;
  payload?: any;
  result_payload?: any;
  created_at: string;
}

export interface AuditLog {
  id: string;
  case_id: string;
  event_type: string;
  actor: string;
  details?: any;
  created_at: string;
}

export interface Notification {
  id: string;
  customer_id: string;
  case_id: string;
  channel: string;
  message: string;
  status: string;
  sent_at: string;
}

export interface CaseListItem {
  id: string;
  case_number: string;
  status: CaseStatus;
  priority: PriorityLevel;
  issue_description: string;
  customer_name: string;
  customer_upi: string;
  transaction_utr: string;
  amount: number;
  tat_deadline: string;
  created_at: string;
}

export interface CaseListResponse {
  total: number;
  active_cases_count: number;
  escalated_count: number;
  resolved_count: number;
  cases: CaseListItem[];
}

export interface CaseDetail {
  id: string;
  case_number: string;
  status: CaseStatus;
  priority: PriorityLevel;
  issue_description: string;
  tat_deadline: string;
  resolution_summary?: string;
  created_at: string;
  updated_at: string;
  customer: Customer;
  transaction: Transaction;
  agent_runs: AgentRun[];
  actions: Action[];
  audit_logs: AuditLog[];
  notifications?: Notification[];
}
