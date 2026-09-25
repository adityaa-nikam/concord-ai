from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
import logging
from app.services.policy_service import PolicyService, TATEvaluator
from app.agents.state import PolicyRecord

logger = logging.getLogger("tat_guardian.policies.tat")


class TATPolicyEngine:
    """NPCI / Paytm TAT Policy Engine wrapping PolicyService & TATEvaluator."""

    @classmethod
    def evaluate(
        cls,
        issue_type: str,
        reconciled_case: str,
        evidence_summary: Dict[str, Any],
        conflicts: List[Dict[str, Any]],
        missing_evidence: List[str],
        tx_created_at: Optional[datetime] = None,
        current_time: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Evaluates policy guidelines, TAT status, and action eligibility."""

        policy: PolicyRecord = PolicyService.retrieve_policy(
            issue_type=issue_type or "DEBITED_BENEFICIARY_NOT_CREDITED"
        )

        tat_status = TATEvaluator.evaluate_tat(
            tx_created_at=tx_created_at or datetime.now(timezone.utc),
            policy_record=policy,
            current_time=current_time
        )

        # Classify eligibility based on explicit reconciliation case & policy rules
        if missing_evidence:
            eligibility = "ESCALATE_TO_HUMAN"
            reason = f"Missing telemetry from: {', '.join(missing_evidence)}."
        elif reconciled_case == "ALREADY_RESOLVED":
            eligibility = "NOTIFY_AND_CLOSE"
            reason = "Reversal has already been executed. No financial action required."
        elif reconciled_case == "CONSISTENT_SUCCESS":
            eligibility = "NOTIFY_AND_CLOSE"
            reason = "Beneficiary Bank confirms credit completed successfully."
        elif reconciled_case == "BENEFICIARY_STATE_UNKNOWN":
            eligibility = "ESCALATE_TO_HUMAN"
            reason = "Beneficiary Bank credit state is UNKNOWN. Escalate for manual verification."
        elif reconciled_case == "PENDING_CONSISTENT":
            eligibility = "WAIT_AND_MONITOR"
            reason = "Transaction pending within 15-minute clearing window buffer."
        elif reconciled_case == "CROSS_SYSTEM_CONFLICT":
            if policy["action_allowed"]:
                eligibility = "AUTO_REVERSAL"
                reason = "Customer debited but beneficiary not credited. Eligible for T+1 auto-reversal."
            else:
                eligibility = "ESCALATE_TO_HUMAN"
                reason = "Cross-system conflict present, but policy disallows auto-reversal for this issue type."
        else:
            eligibility = "ESCALATE_TO_HUMAN"
            reason = "Case state parameters require manual ops inspection."

        return {
            "policy_record": policy,
            "tat_status": tat_status,
            "action_eligibility": eligibility,
            "reason": reason
        }
