from typing import TypedDict, Optional, List, Dict, Any


class ToolCallRecord(TypedDict):
    tool_name: str
    input_payload: Dict[str, Any]
    output_payload: Dict[str, Any]
    status: str
    timestamp: str


class EvidenceItem(TypedDict):
    source: str       # gateway, ledger, beneficiary, reversal, transaction
    field: str        # status, debit_status, credit_status, is_reversed, amount
    value: Any
    timestamp: str


class ConflictRecord(TypedDict):
    conflict_type: str  # GATEWAY_LEDGER_MISMATCH, DEBITED_BENEFICIARY_UNCREDITED, etc.
    description: str
    severity: str        # LOW, MEDIUM, HIGH, CRITICAL
    system_a: str
    system_b: str
    state_a: str
    state_b: str


class PolicyRecord(TypedDict):
    policy_id: str
    policy_name: str
    tat_rule: str        # T_PLUS_1, T_MINUS_BUFFER, MANUAL_REVIEW
    action_allowed: bool
    requires_verification: bool
    escalate_on_conflict: bool
    max_tat_hours: int


class ActionProposal(TypedDict):
    action: str           # INITIATE_REVERSAL, SEND_NOTIFICATION, CREATE_ESCALATION
    transaction_id: str
    case_id: str
    idempotency_key: str  # REVERSAL:{transaction_id}
    reason_code: str
    payload: Dict[str, Any]


class CaseAgentState(TypedDict):
    # Core Identification & Complaint Input
    case_id: str
    case_number: str
    customer_id: str
    transaction_id: str
    utr: str
    customer_message: str
    issue_description: str
    
    # Understand Stage
    extracted_intent: Optional[str]
    extracted_amount: Optional[float]
    extracted_transaction_id: Optional[str]
    issue_type: Optional[str]
    understanding_confidence: float
    is_utr_ambiguous: bool
    prompt_injection_detected: bool


    # Multi-System Diagnostic Evidence Stores
    transaction_data: Optional[Dict[str, Any]]
    gateway_data: Optional[Dict[str, Any]]
    ledger_data: Optional[Dict[str, Any]]
    beneficiary_data: Optional[Dict[str, Any]]
    reversal_data: Optional[Dict[str, Any]]

    # Evidence & Reconciliation Intelligence Layer
    evidence_items: List[EvidenceItem]
    normalized_evidence: List[Dict[str, Any]]
    reconciliation_case: str   # CONSISTENT_SUCCESS, CROSS_SYSTEM_CONFLICT, ALREADY_RESOLVED, PENDING_CONSISTENT, BENEFICIARY_STATE_UNKNOWN
    reconciliation_report: Optional[Dict[str, Any]]
    evidence_summary: Optional[Dict[str, Any]]
    conflicts_detected: List[ConflictRecord]
    missing_evidence: List[str]
    fact_certainty_score: float
    root_cause_hypothesis: Optional[str]

    # Policy Retrieval & RAG Service
    policy_record: Optional[PolicyRecord]
    retrieved_policies: List[Dict[str, Any]]
    tat_status: str            # WITHIN_TAT, TAT_REACHED, TAT_EXCEEDED, UNKNOWN
    action_eligibility: Optional[str]

    # AI Reasoning Layer
    ai_evidence_assessment: Optional[Dict[str, Any]]
    ai_resolution_proposal: Optional[Dict[str, Any]]
    ai_investigation_steps: int
    llm_calls_count: int
    llm_total_latency_ms: float

    # Decision & Resolution Reasoning Engine
    resolution_assessment: Optional[Dict[str, Any]]
    decision: Optional[str]    # ACT, WAIT, ESCALATE, NOTIFY_AND_CLOSE
    action_type: Optional[str] # INITIATE_REVERSAL, SEND_NOTIFICATION, CREATE_ESCALATION
    decision_reason_code: Optional[str]
    decision_reason: Optional[str]


    # Action Gateway & Policy Gate
    action_proposal: Optional[ActionProposal]
    policy_gate_passed: bool
    policy_gate_rejection_reason: Optional[str]
    action_result: Optional[Dict[str, Any]]

    # Post-Action Business Verification
    verification_result: Optional[Dict[str, Any]]
    verification_passed: bool

    # Escalation Packet & Customer Communications
    escalation_reason: Optional[str]
    escalation_packet: Optional[Dict[str, Any]]
    notifications: List[Dict[str, Any]]
    resolution_summary: Optional[str]

    # Lifecycle & Limits
    current_status: str
    steps_completed: int
    current_node: str
    max_steps_limit: int

    # Execution Trace
    tool_calls: List[ToolCallRecord]
    audit_trail: List[Dict[str, Any]]
    errors: List[str]
