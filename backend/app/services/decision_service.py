from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import logging

from app.schemas.reconciliation import ReconciliationResult
from app.policies.schemas import PolicyRecordSchema, PolicyCitation
from app.services.tat_engine import TATEvaluationResult

logger = logging.getLogger("tat_guardian.services.decision")


class ReasonCodes:
    ELIGIBLE_EXCEPTION = "ELIGIBLE_EXCEPTION"
    PENDING_WITHIN_TAT = "PENDING_WITHIN_TAT"
    ALREADY_RESOLVED = "ALREADY_RESOLVED"
    UNRESOLVED_CROSS_SYSTEM_CONFLICT = "UNRESOLVED_CROSS_SYSTEM_CONFLICT"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    POLICY_UNAVAILABLE = "POLICY_UNAVAILABLE"
    ACTION_NOT_PERMITTED = "ACTION_NOT_PERMITTED"
    DUPLICATE_ACTION = "DUPLICATE_ACTION"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    TOOL_FAILURE = "TOOL_FAILURE"
    HIGH_VALUE_THRESHOLD_EXCEEDED = "HIGH_VALUE_THRESHOLD_EXCEEDED"
    PROMPT_INJECTION_ATTEMPT_DETECTED = "PROMPT_INJECTION_ATTEMPT_DETECTED"


class DecisionSupportResult(BaseModel):
    decision: str              # ACT, WAIT, ESCALATE
    reason_code: str           # Standard ReasonCodes constant
    policy_id: str
    action: Optional[str]      # INITIATE_REVERSAL, WAIT_AND_MONITOR, CREATE_ESCALATION
    requires_verification: bool
    escalation_reason: Optional[str] = None
    model_confidence: float
    action_eligibility: str
    idempotency_key: Optional[str] = None


class DecisionSupportService:
    """Decision Support & Policy Gate authorization service."""

    @classmethod
    def evaluate_decision(
        cls,
        reconciliation: ReconciliationResult,
        citations: List[PolicyCitation],
        tat_result: TATEvaluationResult,
        tx_id: Optional[str] = None,
        amount: float = 0.0,
        prompt_injection_detected: bool = False
    ) -> DecisionSupportResult:

        top_citation = citations[0] if citations else PolicyCitation(
            policy_id="POL-UNAVAILABLE",
            source="System",
            source_type="PROTOTYPE_OPERATIONAL",
            section="MANUAL_REVIEW",
            retrieval_relevance=0.0,
            content_excerpt="No policy document available.",
            used_for=["fallback"]
        )

        # 1. Prompt Injection Defense Check
        if prompt_injection_detected:
            logger.warning("Prompt injection attempt detected! Forcing ESCALATE decision.")
            return DecisionSupportResult(
                decision="ESCALATE",
                reason_code=ReasonCodes.PROMPT_INJECTION_ATTEMPT_DETECTED,
                policy_id=top_citation.policy_id,
                action="CREATE_ESCALATION",
                requires_verification=False,
                escalation_reason="Untrusted customer message attempted system prompt injection or policy override.",
                model_confidence=0.99,
                action_eligibility="PROHIBITED_SECURITY_VIOLATION"
            )

        # 2. Already Resolved / Reversal Completed
        if reconciliation.status == "ALREADY_RESOLVED" or reconciliation.reconciled_case_category == "ALREADY_RESOLVED":
            return DecisionSupportResult(
                decision="RESOLVE",
                reason_code=ReasonCodes.ALREADY_RESOLVED,
                policy_id=top_citation.policy_id,
                action="SEND_NOTIFICATION",
                requires_verification=False,
                escalation_reason=None,
                model_confidence=0.98,
                action_eligibility="ALREADY_RESOLVED"
            )

        # 3. High-Value Threshold Check (> ₹50,000)
        if amount > 50000.0 and reconciliation.status == "CONFLICT":
            return DecisionSupportResult(
                decision="ESCALATE",
                reason_code=ReasonCodes.HIGH_VALUE_THRESHOLD_EXCEEDED,
                policy_id=top_citation.policy_id,
                action="CREATE_ESCALATION",
                requires_verification=True,
                escalation_reason=f"Transaction amount ₹{amount} exceeds automated threshold ₹50,000 for cross-system conflicts.",
                model_confidence=0.95,
                action_eligibility="REQUIRES_HUMAN_OPS_OVERRIDE"
            )

        # 4. Incomplete Evidence
        if reconciliation.status == "INCOMPLETE":
            return DecisionSupportResult(
                decision="ESCALATE",
                reason_code=ReasonCodes.INSUFFICIENT_EVIDENCE,
                policy_id=top_citation.policy_id,
                action="CREATE_ESCALATION",
                requires_verification=True,
                escalation_reason=f"Missing essential telemetry: {', '.join(reconciliation.missing_information)}.",
                model_confidence=0.75,
                action_eligibility="ESCALATE_INSUFFICIENT_EVIDENCE"
            )

        # 5. Pending Within TAT Clearing Buffer
        if reconciliation.reconciled_case_category == "PENDING_CONSISTENT" or tat_result.tat_rule == "T_MINUS_BUFFER":
            return DecisionSupportResult(
                decision="WAIT",
                reason_code=ReasonCodes.PENDING_WITHIN_TAT,
                policy_id=top_citation.policy_id,
                action="WAIT_AND_MONITOR",
                requires_verification=True,
                escalation_reason=None,
                model_confidence=0.92,
                action_eligibility="WAIT_CLEARING_WINDOW"
            )

        # 6. Actionable Cross-System Conflict (Auto-Reversal Eligible)
        if reconciliation.status == "CONFLICT" and reconciliation.reconciled_case_category == "CROSS_SYSTEM_CONFLICT":
            idemp_key = f"REVERSAL:{tx_id}" if tx_id else "REVERSAL:UNKNOWN"
            return DecisionSupportResult(
                decision="ACT",
                reason_code=ReasonCodes.ELIGIBLE_EXCEPTION,
                policy_id=top_citation.policy_id,
                action="INITIATE_REVERSAL",
                requires_verification=True,
                escalation_reason=None,
                model_confidence=0.95,
                action_eligibility="AUTO_REVERSAL_PERMITTED",
                idempotency_key=idemp_key
            )

        # 7. Unresolved Conflict Fallback
        return DecisionSupportResult(
            decision="ESCALATE",
            reason_code=ReasonCodes.UNRESOLVED_CROSS_SYSTEM_CONFLICT,
            policy_id=top_citation.policy_id,
            action="CREATE_ESCALATION",
            requires_verification=True,
            escalation_reason=reconciliation.summary,
            model_confidence=0.70,
            action_eligibility="ESCALATE_TO_HUMAN"
        )
