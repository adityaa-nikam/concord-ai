from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from app.schemas.evidence import NormalizedEvidenceSet, EvidenceReliability
from app.services.policy_rag_service import PolicyMatch, PolicyRAGService

logger = logging.getLogger("tat_guardian.agents.reasoning")


class ReasoningSummary(BaseModel):
    facts_grounding: str         # "What happened?" (Grounded in system facts)
    policy_grounding: str        # "What is allowed?" (Grounded in policy rules)
    safety_and_idempotency: str  # "Why is this safe?" (Idempotency key & risk controls)


class ResolutionAssessment(BaseModel):
    decision: str                # ACT, WAIT, ESCALATE, NOTIFY_AND_CLOSE
    proposed_action: str         # INITIATE_REVERSAL, WAIT_AND_POLL, CREATE_ESCALATION, SEND_NOTIFICATION
    reasoning_summary: ReasoningSummary
    confidence_score: float
    requires_human_override: bool
    policy_id_triggered: str
    idempotency_key: Optional[str] = None
    reason_code: str


class ResolutionReasoningEngine:
    """Core Intelligence Engine evaluating facts, policy, and safety to produce auditable decision assessments."""

    @classmethod
    def evaluate_resolution(
        cls,
        reconciled_case: str,
        evidence_summary: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        missing_evidence: List[str],
        policy_matches: List[PolicyMatch],
        nlu_confidence: float = 0.90,
        tx_id: Optional[str] = None
    ) -> ResolutionAssessment:

        top_policy = policy_matches[0] if policy_matches else PolicyMatch(
            policy_id="POL-DEFAULT",
            title="Default Dispute Review",
            clause_reference="GEN-01",
            summary="Default dispute handling",
            rule_condition="None",
            permitted_actions=["CREATE_ESCALATION"],
            prohibited_actions=[],
            auto_execution_allowed=False,
            min_confidence_required=0.90
        )

        debit_status = evidence_summary.get("debit_status", "UNKNOWN")
        credit_status = evidence_summary.get("credit_status", "UNKNOWN")
        gw_status = evidence_summary.get("gateway_status", "UNKNOWN")
        is_reversed = evidence_summary.get("is_reversed", False)
        amount = evidence_summary.get("amount", 0.0) or 0.0

        # Validate top policy against facts
        fact_validation = PolicyRAGService.validate_policy_against_facts(
            top_policy,
            {"is_reversed": is_reversed, "amount": amount}
        )

        # 1. Fact Grounding
        facts_text = (
            f"Remitter ledger status is '{debit_status}', Beneficiary credit status is '{credit_status}', "
            f"and Payment Gateway status is '{gw_status}'. "
            f"Reconciliation classified transaction as '{reconciled_case}' with {len(conflicts)} conflict(s) detected."
        )

        # 2. Decision Logic
        if is_reversed or reconciled_case == "ALREADY_RESOLVED":
            decision = "NOTIFY_AND_CLOSE"
            proposed_action = "SEND_NOTIFICATION"
            reason_code = "REVERSAL_ALREADY_COMPLETED"
            policy_text = f"Governed by '{top_policy.title}' ({top_policy.clause_reference}). Reversal has already been processed."
            safety_text = f"Idempotency Guard ACTIVE: Transaction {tx_id} is already reversed. Duplicate reversal blocked."
            confidence = 0.98
            requires_override = False
            idempotency_key = None

        elif missing_evidence or debit_status == "ON_HOLD" or reconciled_case == "BENEFICIARY_STATE_UNKNOWN" or not fact_validation["valid"] or amount > 50000.0:
            decision = "ESCALATE"
            proposed_action = "CREATE_ESCALATION"
            reason_code = "AMBIGUOUS_OR_HIGH_RISK_EXCEPTION"
            
            if amount > 50000.0:
                policy_text = f"Governed by '{top_policy.title}' ({top_policy.clause_reference}). Transaction amount ₹{amount} exceeds automated safety limit ₹50,000."
                safety_text = "Risk Threshold Safeguard TRIGGERED: High-value transaction requires Tier 2 Human Ops authorization."
            elif missing_evidence:
                policy_text = f"Governed by '{top_policy.title}'. Telemetry missing from {', '.join(missing_evidence)}."
                safety_text = "Completeness Safeguard TRIGGERED: Cannot execute automated action without 5-source evidence verification."
            else:
                policy_text = f"Governed by '{top_policy.title}' ({top_policy.clause_reference}). State ambiguity present."
                safety_text = f"Safety Lock ACTIVE: {fact_validation.get('reason', 'Ambiguous state requires human verification.')}"

            confidence = 0.70
            requires_override = True
            idempotency_key = None

        elif reconciled_case == "PENDING_CONSISTENT":
            decision = "WAIT"
            proposed_action = "WAIT_AND_POLL"
            reason_code = "CLEARING_WINDOW_MONITORING"
            policy_text = f"Governed by '{top_policy.title}' ({top_policy.clause_reference}). Transaction is pending within NPCI clearing window."
            safety_text = "Monitoring Mode ACTIVE: Agent will schedule background status poll before deciding final action."
            confidence = 0.92
            requires_override = False
            idempotency_key = None

        elif reconciled_case == "CONSISTENT_SUCCESS":
            decision = "NOTIFY_AND_CLOSE"
            proposed_action = "SEND_NOTIFICATION"
            reason_code = "CREDIT_CONFIRMED_SUCCESS"
            policy_text = f"Governed by '{top_policy.title}'. Beneficiary bank confirms credit completed."
            safety_text = "Verification Complete: Customer claim resolved. No financial adjustment needed."
            confidence = 0.96
            requires_override = False
            idempotency_key = None

        elif reconciled_case == "CROSS_SYSTEM_CONFLICT" and debit_status == "DEBITED" and credit_status == "NOT_CREDITED" and top_policy.auto_execution_allowed:
            decision = "ACT"
            proposed_action = "INITIATE_REVERSAL"
            reason_code = "NPCI_T1_AUTO_REVERSAL_ELIGIBLE"
            policy_text = f"Governed by '{top_policy.title}' ({top_policy.clause_reference}). Auto-reversal is permitted under NPCI T+1 rules."
            idemp_key = f"REVERSAL:{tx_id}" if tx_id else "REVERSAL:UNKNOWN"
            safety_text = f"Idempotency Key locked as '{idemp_key}'. Multi-source outcome verification will be enforced post-action."
            confidence = min(nlu_confidence, 0.95)
            requires_override = False
            idempotency_key = idemp_key

        else:
            decision = "ESCALATE"
            proposed_action = "CREATE_ESCALATION"
            reason_code = "UNHANDLED_EXCEPTION_STATE"
            policy_text = f"Governed by '{top_policy.title}'. State parameters require manual review."
            safety_text = "Manual Fallback: Routing to Tier 2 Human Ops Queue."
            confidence = 0.65
            requires_override = True
            idempotency_key = None

        summary = ReasoningSummary(
            facts_grounding=facts_text,
            policy_grounding=policy_text,
            safety_and_idempotency=safety_text
        )

        logger.info(f"Resolution reasoning engine output: decision={decision}, action={proposed_action}, confidence={confidence}")

        return ResolutionAssessment(
            decision=decision,
            proposed_action=proposed_action,
            reasoning_summary=summary,
            confidence_score=confidence,
            requires_human_override=requires_override,
            policy_id_triggered=top_policy.policy_id,
            idempotency_key=idempotency_key,
            reason_code=reason_code
        )
