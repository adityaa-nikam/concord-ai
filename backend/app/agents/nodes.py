from datetime import datetime, timezone
from typing import Dict, Any, List
import logging
from sqlalchemy.orm import Session

from app.agents.state import CaseAgentState, ToolCallRecord, ActionProposal
from app.agents.understand import CustomerComplaintUnderstandEngine
from app.schemas.evidence import EvidenceItem, EvidenceReliability, EvidenceFreshness
from app.services.evidence_service import EvidenceNormalizationService
from app.schemas.reconciliation import DeterministicReconciliationEngine, ReconciliationResult
from app.policies.retriever import PolicyRAGRetriever
from app.services.tat_engine import DeterministicTATEngine
from app.services.decision_service import DecisionSupportService, ReasonCodes
from app.services.summary_service import CaseSummaryService
from app.policies.loader import PolicyDocumentLoader
from app.policies.schemas import PolicyCitation
from app.services.action_gateway import PolicyGate, ActionGateway
from app.tools.fintech_tools import FintechTools
from app.models.domain import Case, CaseStatus
from app.core.llm_provider import LLMProvider, AIEvidenceAssessment, AIResolutionProposal

logger = logging.getLogger("tat_guardian.agents.nodes")

# ... (check_max_steps, record_tool_call, record_audit remain unchanged)



def check_max_steps(state: CaseAgentState) -> bool:
    max_limit = state.get("max_steps_limit", 15)
    if state["steps_completed"] >= max_limit:
        logger.warning(f"Execution step limit {max_limit} exceeded for case {state['case_id']}. Halting.")
        state["errors"].append(f"EXECUTION_LIMIT_EXCEEDED: Step limit of {max_limit} steps exceeded.")
        return True
    return False


def record_tool_call(state: CaseAgentState, tool_name: str, input_p: Dict[str, Any], output_p: Dict[str, Any], status: str = "SUCCESS"):
    record: ToolCallRecord = {
        "tool_name": tool_name,
        "input_payload": input_p,
        "output_payload": output_p,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    state["tool_calls"].append(record)
    state["steps_completed"] += 1


def record_audit(state: CaseAgentState, event_type: str, details: Dict[str, Any]):
    state["audit_trail"].append({
        "event_type": event_type,
        "actor": "CONCORD_AI",
        "details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })


def intake_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """1. INTAKE Node: Loads complaint text and transaction metadata."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: intake] Intake case {state['case_id']}")
    tools = FintechTools(db)

    tx_data = tools.get_transaction(state["transaction_id"])
    record_tool_call(state, "get_transaction", {"transaction_id": state["transaction_id"]}, tx_data)

    state["transaction_data"] = tx_data
    if tx_data and "utr" in tx_data:
        state["utr"] = tx_data["utr"]

    state["customer_message"] = state.get("issue_description") or ""
    state["current_status"] = "INVESTIGATING"
    state["current_node"] = "understand"
    record_audit(state, "CASE_CREATED", {"case_id": state["case_id"], "utr": state.get("utr")})
    return state


def understand_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """2. UNDERSTAND Node: Converts customer complaint into structured NLU intent with Prompt Injection Defense."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: understand] Parsing complaint text for case {state['case_id']}")

    msg_text = state.get("customer_message", "")
    injection_keywords = ["ignore policy", "ignore rules", "override policy", "refund me twice", "system rule:", "system prompt"]
    is_injection = any(k in msg_text.lower() for k in injection_keywords)
    state["prompt_injection_detected"] = is_injection

    if is_injection:
        logger.warning(f"Prompt injection attempt detected in customer text: '{msg_text}'")
        record_audit(state, "PROMPT_INJECTION_DETECTED", {"customer_text": msg_text})

    default_amt = state.get("transaction_data", {}).get("amount") if state.get("transaction_data") else None
    default_utr = state.get("utr")

    parsed = CustomerComplaintUnderstandEngine.parse_complaint(
        text=msg_text,
        case_id=state["case_id"],
        db=db,
        default_amount=default_amt,
        default_utr=default_utr
    )

    state["extracted_intent"] = parsed["extracted_intent"]
    state["extracted_amount"] = parsed["extracted_amount"]
    state["extracted_transaction_id"] = parsed["extracted_utr"]
    state["issue_type"] = parsed["issue_type"]
    state["understanding_confidence"] = parsed["confidence"]
    state["is_utr_ambiguous"] = parsed["is_utr_ambiguous"]

    state["current_node"] = "investigate"
    record_audit(state, "COMPLAINT_PARSED", parsed)
    return state


def investigate_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """3. INVESTIGATE Node: Multi-system telemetry query loop."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: investigate] Gathering multi-system evidence for UTR {state.get('utr')}")
    tools = FintechTools(db)
    tx_id = state["transaction_id"]

    # 1. Gateway Status
    gw_res = tools.get_payment_gateway_status(tx_id)
    record_tool_call(state, "get_payment_gateway_status", {"transaction_id": tx_id}, gw_res)
    state["gateway_data"] = gw_res

    # 2. Bank Ledger Status
    ledger_res = tools.get_ledger_status(tx_id)
    record_tool_call(state, "get_ledger_status", {"transaction_id": tx_id}, ledger_res)
    state["ledger_data"] = ledger_res

    # 3. Beneficiary Bank Status
    bene_res = tools.get_beneficiary_status(tx_id)
    record_tool_call(state, "get_beneficiary_status", {"transaction_id": tx_id}, bene_res)
    state["beneficiary_data"] = bene_res

    # 4. Reversal Status
    rev_res = tools.get_reversal_status(tx_id)
    record_tool_call(state, "get_reversal_status", {"transaction_id": tx_id}, rev_res)
    state["reversal_data"] = rev_res

    state["current_node"] = "reconcile"
    record_audit(state, "EVIDENCE_COLLECTED", {
        "gateway": gw_res.get("gateway_status"),
        "ledger": ledger_res.get("debit_status"),
        "beneficiary": bene_res.get("credit_status")
    })
    return state


def reconcile_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """4. RECONCILE Node: Transforms evidence into NormalizedEvidenceSet and runs DeterministicReconciliationEngine."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: reconcile] Reconciling evidence for case {state['case_id']}")

    tx_d = state.get("transaction_data") or {}
    gw_d = state.get("gateway_data") or {}
    ledger_d = state.get("ledger_data") or {}
    bene_d = state.get("beneficiary_data") or {}
    rev_d = state.get("reversal_data") or {}

    # 1. Evidence Normalization
    ev_set = EvidenceNormalizationService.normalize_evidence_set(
        tx_data=tx_d,
        gw_data=gw_d,
        ledger_data=ledger_d,
        bene_data=bene_d,
        rev_data=rev_d,
        customer_msg=state.get("customer_message"),
        extracted_amount=state.get("extracted_amount")
    )
    state["normalized_evidence"] = [item.model_dump() for item in ev_set.items]

    # 2. Deterministic Reconciliation
    recon_res = DeterministicReconciliationEngine.reconcile_evidence_set(ev_set)

    state["reconciliation_case"] = recon_res.reconciled_case_category
    state["reconciliation_report"] = recon_res.model_dump()
    state["evidence_summary"] = {
        "utr": state.get("utr"),
        "amount": tx_d.get("amount") or state.get("extracted_amount"),
        "debit_status": (ledger_d.get("debit_status") or "UNKNOWN").upper(),
        "credit_status": (bene_d.get("credit_status") or "UNKNOWN").upper(),
        "gateway_status": (gw_d.get("gateway_status") or "UNKNOWN").upper(),
        "npci_status": (gw_d.get("npci_status") or "UNKNOWN").upper(),
        "is_reversed": rev_d.get("is_reversed", False) or (tx_d.get("status") == "REVERSED"),
        "reconciled_case": recon_res.reconciled_case_category,
        "has_conflicts": len(recon_res.conflicts) > 0,
        "primary_conflict": recon_res.conflicts[0].conflict_type if recon_res.conflicts else "NONE"
    }
    state["conflicts_detected"] = [c.model_dump() for c in recon_res.conflicts]
    state["missing_evidence"] = recon_res.missing_information
    state["fact_certainty_score"] = 1.0 if not recon_res.conflicts else 0.85
    state["root_cause_hypothesis"] = recon_res.summary

    state["current_status"] = "AI_EVIDENCE_INTERPRETATION"
    state["current_node"] = "ai_evidence_interpretation"

    record_audit(state, "RECONCILIATION_COMPLETED", {
        "status": recon_res.status,
        "category": recon_res.reconciled_case_category,
        "conflicts_count": len(recon_res.conflicts)
    })
    return state


def ai_evidence_interpretation_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """4.5. AI EVIDENCE INTERPRETATION Node: Reasons broadly over evidence and recommends next tools if telemetry is missing."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: ai_evidence_interpretation] Assessing evidence via LLM for case {state['case_id']}")

    msg = state.get("customer_message") or state.get("issue_description") or ""
    norm_ev = state.get("normalized_evidence") or []
    recon_report = state.get("reconciliation_report") or {}
    recon_summary = recon_report.get("summary") or ""
    recon_cat = state.get("reconciliation_case") or "CROSS_SYSTEM_CONFLICT"
    conflicts = state.get("conflicts_detected") or []
    missing_fields = state.get("missing_evidence") or []
    already_called_tools = [tc.get("tool_name") for tc in state.get("tool_calls", [])]

    assessment = LLMProvider.assess_evidence(
        customer_message=msg,
        normalized_evidence=norm_ev,
        reconciliation_summary=recon_summary,
        reconciled_category=recon_cat,
        conflicts=conflicts,
        missing_fields=missing_fields,
        already_called_tools=already_called_tools
    )

    state["ai_evidence_assessment"] = assessment.model_dump()
    state["llm_calls_count"] = (state.get("llm_calls_count") or 0) + 1

    # Bounded Investigation Loop: If LLM recommends missing tool telemetry
    max_inv_steps = 3
    current_inv_steps = state.get("ai_investigation_steps") or 0

    # Dynamically filter out tools that have ALREADY been executed
    uncalled_recommendations = [t for t in assessment.recommended_next_evidence if t not in set(already_called_tools)]

    if uncalled_recommendations and current_inv_steps < max_inv_steps:
        tools = FintechTools(db)
        tx_id = state["transaction_id"]
        allowlisted_tools = ["get_payment_gateway_status", "get_ledger_status", "get_beneficiary_status", "get_reversal_status"]

        for tool_req in uncalled_recommendations:
            if tool_req in allowlisted_tools:
                logger.info(f"[AI INVESTIGATION LOOP] Invoking AI-recommended tool: {tool_req}")
                if tool_req == "get_beneficiary_status":
                    bene_res = tools.get_beneficiary_status(tx_id)
                    state["beneficiary_data"] = bene_res
                    record_tool_call(state, "get_beneficiary_status", {"transaction_id": tx_id}, bene_res)
                elif tool_req == "get_ledger_status":
                    ledger_res = tools.get_ledger_status(tx_id)
                    state["ledger_data"] = ledger_res
                    record_tool_call(state, "get_ledger_status", {"transaction_id": tx_id}, ledger_res)

                state["ai_investigation_steps"] = current_inv_steps + 1
                ev_set = EvidenceNormalizationService.normalize_evidence_set(
                    tx_data=state.get("transaction_data"),
                    gw_data=state.get("gateway_data"),
                    ledger_data=state.get("ledger_data"),
                    bene_data=state.get("beneficiary_data"),
                    rev_data=state.get("reversal_data")
                )
                state["normalized_evidence"] = [i.model_dump() for i in ev_set.items]
                break

    state["current_status"] = "POLICY_CHECK"
    state["current_node"] = "policy_check"

    record_audit(state, "AI_EVIDENCE_ASSESSED", {
        "assessment": assessment.assessment,
        "facts_count": len(assessment.known_facts),
        "uncertainties_count": len(assessment.uncertainties),
        "recommended_next_evidence": assessment.recommended_next_evidence,
        "reasoning": assessment.reasoning_summary
    })
    return state


def policy_check_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """5. POLICY CHECK Node: Retrieves citations via PolicyRAGRetriever and evaluates TAT with DeterministicTATEngine."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: policy_check] Evaluating policy & TAT for case {state['case_id']}")

    retriever = PolicyRAGRetriever()
    tx_d = state.get("transaction_data") or {}
    ev_sum = state.get("evidence_summary") or {}
    amount_val = tx_d.get("amount") or state.get("extracted_amount") or 0.0

    # Determine transaction type
    payee_upi = tx_d.get("payee_upi", "")
    tx_type = "UPI_MERCHANT_PAYMENT" if "merchant" in payee_upi.lower() or "swiggy" in payee_upi.lower() else "UPI_TRANSFER"

    # 1. Retrieve Policy Citations
    citations = retriever.retrieve_policies(
        transaction_type=tx_type,
        reconciled_case_category=state.get("reconciliation_case") or "CROSS_SYSTEM_CONFLICT",
        amount=amount_val,
        debit_status=ev_sum.get("debit_status", "UNKNOWN"),
        credit_status=ev_sum.get("credit_status", "UNKNOWN"),
        is_reversed=ev_sum.get("is_reversed", False),
        missing_evidence=state.get("missing_evidence") or []
    )
    state["retrieved_policies"] = [c.model_dump() for c in citations]

    # 2. Evaluate TAT with injectable clock
    top_policy_doc = retriever.get_policy_by_id(citations[0].policy_id) if citations else None
    if not top_policy_doc:
        top_policy_doc = retriever._policies[0]

    tx_created = None
    if tx_d and "created_at" in tx_d:
        try:
            tx_created = datetime.fromisoformat(str(tx_d["created_at"]).replace("Z", "+00:00"))
        except Exception:
            pass

    tat_eval = DeterministicTATEngine.evaluate_tat(
        policy=top_policy_doc,
        tx_created_at=tx_created,
        transaction_type=tx_type
    )

    state["policy_record"] = {
        "policy_id": top_policy_doc.policy_id,
        "policy_name": top_policy_doc.title,
        "tat_rule": top_policy_doc.tat_rule,
        "action_allowed": "INITIATE_REVERSAL" in top_policy_doc.allowed_actions,
        "requires_verification": len(top_policy_doc.verification_requirements) > 0,
        "escalate_on_conflict": True,
        "max_tat_hours": tat_eval.max_tat_hours
    }
    state["tat_status"] = tat_eval.tat_status
    state["action_eligibility"] = "AUTO_REVERSAL" if "INITIATE_REVERSAL" in top_policy_doc.allowed_actions and state.get("reconciliation_case") == "CROSS_SYSTEM_CONFLICT" else "ESCALATE_TO_HUMAN"

    state["current_status"] = "AI_RESOLUTION_PROPOSAL"
    state["current_node"] = "ai_resolution_proposal"

    record_audit(state, "POLICY_RETRIEVED", {
        "top_policy": citations[0].policy_id,
        "source": citations[0].source,
        "tat_status": tat_eval.tat_status,
        "compensation": tat_eval.compensation_amount
    })
    return state


def ai_resolution_proposal_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """5.5. AI RESOLUTION PROPOSAL Node: Obtains structured resolution proposal from LLMProvider."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: ai_resolution_proposal] Generating resolution proposal via LLM for case {state['case_id']}")

    msg = state.get("customer_message") or state.get("issue_description") or ""
    tx_d = state.get("transaction_data") or {}
    amount_val = tx_d.get("amount") or state.get("extracted_amount") or 0.0
    recon_report = state.get("reconciliation_report") or {}
    recon_obj = ReconciliationResult(**recon_report) if recon_report else DeterministicReconciliationEngine.reconcile_evidence_set(EvidenceNormalizationService.normalize_evidence_set())

    retriever = PolicyRAGRetriever()
    citations = [PolicyCitation(**c) for c in state.get("retrieved_policies", [])] if state.get("retrieved_policies") else retriever.retrieve_policies("UPI_TRANSFER", "CROSS_SYSTEM_CONFLICT")
    top_policy_doc = retriever.get_policy_by_id(citations[0].policy_id) if citations else retriever._policies[0]
    tat_eval = DeterministicTATEngine.evaluate_tat(policy=top_policy_doc, tx_created_at=None)

    proposal = LLMProvider.propose_resolution(
        customer_message=msg,
        reconciliation=recon_obj,
        citations=citations,
        tat_result=tat_eval,
        amount=amount_val,
        prompt_injection_detected=state.get("prompt_injection_detected", False)
    )

    state["ai_resolution_proposal"] = proposal.model_dump()
    state["llm_calls_count"] = (state.get("llm_calls_count") or 0) + 1

    state["current_status"] = "DECISION"
    state["current_node"] = "decision"

    record_audit(state, "AI_DECISION_PROPOSED", {
        "proposed_decision": proposal.decision,
        "proposed_action": proposal.action,
        "reason_code": proposal.reason_code,
        "confidence": proposal.confidence,
        "reasoning_summary": proposal.reasoning_summary
    })
    return state


def decision_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """6. DECISION Node: Evaluates DecisionSupportService with machine-readable ReasonCodes."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: decision] Evaluating decision for case {state['case_id']}")

    retriever = PolicyRAGRetriever()
    tx_d = state.get("transaction_data") or {}
    ev_sum = state.get("evidence_summary") or {}
    amount_val = tx_d.get("amount") or state.get("extracted_amount") or 0.0

    payee_upi = tx_d.get("payee_upi", "")
    tx_type = "UPI_MERCHANT_PAYMENT" if "merchant" in payee_upi.lower() or "swiggy" in payee_upi.lower() else "UPI_TRANSFER"

    citations = retriever.retrieve_policies(
        transaction_type=tx_type,
        reconciled_case_category=state.get("reconciliation_case") or "CROSS_SYSTEM_CONFLICT",
        amount=amount_val,
        debit_status=ev_sum.get("debit_status", "UNKNOWN"),
        credit_status=ev_sum.get("credit_status", "UNKNOWN"),
        is_reversed=ev_sum.get("is_reversed", False),
        missing_evidence=state.get("missing_evidence") or []
    )

    top_policy_doc = retriever.get_policy_by_id(citations[0].policy_id) if citations else retriever._policies[0]
    
    tx_created = None
    if tx_d and "created_at" in tx_d:
        try:
            tx_created = datetime.fromisoformat(str(tx_d["created_at"]).replace("Z", "+00:00"))
        except Exception:
            pass

    tat_eval = DeterministicTATEngine.evaluate_tat(policy=top_policy_doc, tx_created_at=tx_created)

    recon_report = state.get("reconciliation_report")
    if recon_report and isinstance(recon_report, dict):
        recon_obj = ReconciliationResult(**recon_report)
    else:
        recon_obj = DeterministicReconciliationEngine.reconcile_evidence_set(
            EvidenceNormalizationService.normalize_evidence_set(tx_data=tx_d, gw_data=state.get("gateway_data"))
        )

    decision_res = DecisionSupportService.evaluate_decision(
        reconciliation=recon_obj,
        citations=citations,
        tat_result=tat_eval,
        tx_id=state.get("transaction_id"),
        amount=amount_val,
        prompt_injection_detected=state.get("prompt_injection_detected", False)
    )

    state["decision"] = decision_res.decision
    state["action_type"] = decision_res.action
    state["decision_reason_code"] = decision_res.reason_code
    state["decision_reason"] = f"[{decision_res.reason_code}] {decision_res.action_eligibility}. Policy: {decision_res.policy_id}."

    if decision_res.decision == "ACT":
        state["current_status"] = "ACTION_REQUIRED"
        state["current_node"] = "policy_gate"
        tx_id = state["transaction_id"]
        state["action_proposal"] = {
            "action": "INITIATE_REVERSAL",
            "transaction_id": tx_id,
            "case_id": state["case_id"],
            "idempotency_key": decision_res.idempotency_key or f"REVERSAL:{tx_id}",
            "reason_code": decision_res.reason_code,
            "payload": {"utr": state.get("utr"), "amount": amount_val}
        }
    elif decision_res.decision == "WAIT":
        state["current_status"] = "INVESTIGATING"
        state["current_node"] = "wait"
    else:
        state["current_status"] = "ESCALATED" if decision_res.decision == "ESCALATE" else "RESOLVED"
        state["current_node"] = "escalation" if decision_res.decision == "ESCALATE" else "resolution"

    record_audit(state, "DECISION_MADE", {
        "decision": decision_res.decision,
        "action": decision_res.action,
        "reason_code": decision_res.reason_code,
        "policy_id": decision_res.policy_id
    })
    return state


def policy_gate_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """7. POLICY GATE Node: Authorizes or rejects action proposal."""
    proposal = state.get("action_proposal")
    policy_rec = state.get("policy_record")
    missing_ev = state.get("missing_evidence") or []
    is_already_resolved = (state.get("reconciliation_case") == "ALREADY_RESOLVED")

    gate_check = PolicyGate.validate_action_proposal(
        proposal=proposal,
        policy_record=policy_rec,
        missing_evidence=missing_ev,
        is_already_resolved=is_already_resolved
    )

    state["policy_gate_passed"] = gate_check["passed"]
    state["policy_gate_rejection_reason"] = gate_check.get("reason") if not gate_check["passed"] else None

    if gate_check["passed"]:
        record_audit(state, "ACTION_AUTHORIZED", {"action_proposal": proposal})
        state["current_node"] = "action"
    else:
        record_audit(state, "ACTION_REJECTED_BY_POLICY_GATE", {"reason": gate_check["reason"]})
        state["decision"] = "ESCALATE"
        state["decision_reason"] = gate_check["reason"]
        state["current_status"] = "ESCALATED"
        state["current_node"] = "escalation"

    return state


def action_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """8. ACTION GATEWAY Node: Executes authorized action through ActionGateway enforcing idempotency key."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    proposal = state.get("action_proposal")
    logger.info(f"[NODE: action] Executing action proposal {proposal.get('action')} with key {proposal.get('idempotency_key')}")

    gateway = ActionGateway(db)
    result = gateway.execute_action_proposal(proposal)

    record_tool_call(state, "initiate_reversal", proposal.get("payload", {}), result)
    state["action_result"] = result

    record_audit(state, "ACTION_EXECUTED", result)
    state["current_status"] = "VERIFYING"
    state["current_node"] = "verification"
    return state


def wait_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """WAIT / MONITOR Node: Handles pending transaction monitoring state."""
    reason = state.get("decision_reason") or "Pending transaction within TAT clearing window."
    state["resolution_summary"] = f"WAIT AND MONITOR: {reason}"
    state["current_status"] = "INVESTIGATING"
    state["current_node"] = "end"
    record_audit(state, "MONITORING_STATE_SET", {"reason": reason, "tat_status": state.get("tat_status")})
    return state


def verification_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """9. VERIFICATION Node: Re-queries services post-action and enforces multi-source verification rules."""
    if check_max_steps(state):
        state["current_node"] = "escalation"
        return state

    logger.info(f"[NODE: verification] Re-querying systems post-action for case {state['case_id']}")
    record_audit(state, "VERIFICATION_STARTED", {"transaction_id": state["transaction_id"]})
    tools = FintechTools(db)
    tx_id = state["transaction_id"]

    # Re-query independent sources post-action
    ledger_check = tools.get_ledger_status(tx_id)
    rev_check = tools.get_reversal_status(tx_id)

    record_tool_call(state, "get_reversal_status", {"transaction_id": tx_id}, rev_check)

    is_reversal_completed = rev_check.get("is_reversed", False) or rev_check.get("status") == "COMPLETED"
    is_ledger_reversed = ledger_check.get("debit_status") == "REVERSED"

    if is_reversal_completed and is_ledger_reversed:
        state["verification_passed"] = True
        state["verification_result"] = {
            "status": "VERIFIED_SUCCESS",
            "reversal_status": rev_check.get("status"),
            "ledger_status": ledger_check.get("debit_status")
        }
        record_audit(state, "VERIFICATION_SUCCEEDED", state["verification_result"])
        state["current_status"] = "RESOLVED"
        state["current_node"] = "resolution"
    else:
        state["verification_passed"] = False
        state["verification_result"] = {
            "status": "VERIFICATION_FAILED",
            "reversal_status": rev_check.get("status"),
            "ledger_status": ledger_check.get("debit_status"),
            "error": "Post-action verification failed: Ledger or Reversal status inconsistent."
        }
        record_audit(state, "VERIFICATION_FAILED", state["verification_result"])
        state["decision"] = "ESCALATE"
        state["decision_reason_code"] = ReasonCodes.VERIFICATION_FAILED
        state["decision_reason"] = "Post-action verification failed. Financial outcome could not be verified across systems."
        state["current_status"] = "ESCALATED"
        state["current_node"] = "escalation"

    return state


def resolution_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """10. RESOLUTION Node: Dispatches customer notification and closes case with operational summary."""
    logger.info(f"[NODE: resolution] Resolving case {state['case_id']}")
    tools = FintechTools(db)

    msg = f"Paytm Dispute Update (Case {state['case_number']}): Your payment issue for transaction UTR {state.get('utr')} has been resolved. The reversal has been verified."

    notif_res = tools.send_customer_notification(
        customer_id=state["customer_id"],
        case_id=state["case_id"],
        message=msg
    )
    record_tool_call(state, "send_customer_notification", {"customer_id": state["customer_id"], "message": msg}, notif_res)

    state["notifications"].append(notif_res)
    record_audit(state, "CUSTOMER_NOTIFIED", {"notification_type": "RESOLVED", "message": msg})

    # Generate Case Summary via CaseSummaryService
    summary = CaseSummaryService.generate_case_summary(
        case_number=state["case_number"],
        issue_description=state.get("issue_description", ""),
        amount=state.get("extracted_amount") or 0.0,
        reconciliation=ReconciliationResult(**state["reconciliation_report"]) if state.get("reconciliation_report") else DeterministicReconciliationEngine.reconcile_evidence_set(EvidenceNormalizationService.normalize_evidence_set()),
        decision_res=DecisionSupportService.evaluate_decision(
            reconciliation=ReconciliationResult(**state["reconciliation_report"]) if state.get("reconciliation_report") else DeterministicReconciliationEngine.reconcile_evidence_set(EvidenceNormalizationService.normalize_evidence_set()),
            citations=[PolicyRAGRetriever().retrieve_policies("UPI_TRANSFER", "CROSS_SYSTEM_CONFLICT")[0]],
            tat_result=DeterministicTATEngine.evaluate_tat(PolicyDocumentLoader.load_all_policies()[0], None)
        ),
        verification_passed=state.get("verification_passed", True),
        is_resolved=True
    )
    state["resolution_summary"] = summary
    state["current_status"] = "RESOLVED"
    state["current_node"] = "end"

    case = db.query(Case).filter(Case.id == state["case_id"]).first()
    if case:
        case.status = CaseStatus.RESOLVED
        case.resolution_summary = summary
        db.commit()

    record_audit(state, "CASE_RESOLVED", {"summary": summary})
    return state


def escalation_node(state: CaseAgentState, db: Session) -> CaseAgentState:
    """11. ESCALATION Node: Builds comprehensive Ops Evidence Packet for Tier 2 Ops."""
    logger.info(f"[NODE: escalation] Escalating case {state['case_id']}")
    tools = FintechTools(db)

    reason = state.get("decision_reason") or "Unresolved cross-system conflict requiring human ops intervention."

    gw_data = state.get("gateway_data") or {}
    ledger_data = state.get("ledger_data") or {}
    bene_data = state.get("beneficiary_data") or {}
    rev_data = state.get("reversal_data") or {}
    policy_rec = state.get("policy_record") or {}
    action_prop = state.get("action_proposal") or {}
    ver_res = state.get("verification_result") or {}

    escalation_pkt = {
        "case_id": state["case_id"],
        "case_number": state["case_number"],
        "transaction_id": state["transaction_id"],
        "utr": state.get("utr"),
        "customer_issue": state.get("issue_description"),
        "gateway_result": gw_data.get("gateway_status"),
        "ledger_result": ledger_data.get("debit_status"),
        "beneficiary_result": bene_data.get("credit_status"),
        "reversal_result": rev_data.get("status"),
        "policy": policy_rec.get("policy_id"),
        "tat": state.get("tat_status"),
        "conflicts": state.get("conflicts_detected", []),
        "actions_attempted": [action_prop.get("action")] if action_prop.get("action") else [],
        "verification_status": ver_res.get("status", "NOT_PERFORMED"),
        "recommended_next_step": "Investigate gateway-ledger reconciliation in Core Banking System."
    }

    state["escalation_reason"] = reason
    state["escalation_packet"] = escalation_pkt

    esc_res = tools.create_human_escalation(
        case_id=state["case_id"],
        reason=reason,
        details=escalation_pkt
    )
    record_tool_call(state, "create_human_escalation", {"case_id": state["case_id"], "reason": reason}, esc_res)

    record_audit(state, "ESCALATED", escalation_pkt)
    state["resolution_summary"] = f"ESCALATED TO OPS TIER 2: {reason}"
    state["current_status"] = "ESCALATED"
    state["current_node"] = "end"
    return state
