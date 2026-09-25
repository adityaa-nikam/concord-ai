from datetime import datetime, timezone
from typing import Dict, Any, Optional
import logging
from app.agents.state import PolicyRecord

logger = logging.getLogger("tat_guardian.services.policy")


class PolicyService:
    """Explicit Policy Knowledge Service for retrieving resolution guidelines."""

    POLICIES = {
        "DEBITED_BENEFICIARY_NOT_CREDITED": {
            "policy_id": "UPI_TRANSFER_DEBITED_NOT_CREDITED",
            "policy_name": "NPCI T+1 Auto-Reversal for Failed UPI Transactions",
            "tat_rule": "T_PLUS_1",
            "action_allowed": True,
            "requires_verification": True,
            "escalate_on_conflict": True,
            "max_tat_hours": 24
        },
        "PENDING_TRANSACTION_STATUS": {
            "policy_id": "UPI_CLEARING_WINDOW_BUFFER",
            "policy_name": "NPCI 15-Minute Clearing Buffer",
            "tat_rule": "T_MINUS_BUFFER",
            "action_allowed": False,
            "requires_verification": True,
            "escalate_on_conflict": False,
            "max_tat_hours": 1
        },
        "REVERSAL_STATUS_INQUIRY": {
            "policy_id": "UPI_REVERSAL_STATUS_VERIFY",
            "policy_name": "Reversal Status Verification",
            "tat_rule": "IMMEDIATE",
            "action_allowed": False,
            "requires_verification": True,
            "escalate_on_conflict": False,
            "max_tat_hours": 24
        }
    }

    @classmethod
    def retrieve_policy(
        cls,
        issue_type: str,
        transaction_type: str = "UPI",
        evidence: Optional[Dict[str, Any]] = None
    ) -> PolicyRecord:
        """Retrieves structured policy record by issue type and evidence."""
        p = cls.POLICIES.get(issue_type)
        if not p:
            # Default fallback policy
            p = {
                "policy_id": "UPI_MANUAL_REVIEW_FALLBACK",
                "policy_name": "Manual Ops Dispute Review",
                "tat_rule": "MANUAL_REVIEW",
                "action_allowed": False,
                "requires_verification": True,
                "escalate_on_conflict": True,
                "max_tat_hours": 48
            }

        return PolicyRecord(
            policy_id=p["policy_id"],
            policy_name=p["policy_name"],
            tat_rule=p["tat_rule"],
            action_allowed=p["action_allowed"],
            requires_verification=p["requires_verification"],
            escalate_on_conflict=p["escalate_on_conflict"],
            max_tat_hours=p["max_tat_hours"]
        )


class TATEvaluator:
    """Deterministic TAT Calculator with clock dependency injection for unit testing."""

    @classmethod
    def evaluate_tat(
        cls,
        tx_created_at: datetime,
        policy_record: PolicyRecord,
        current_time: Optional[datetime] = None
    ) -> str:
        """Evaluates whether transaction is WITHIN_TAT, TAT_REACHED, or TAT_EXCEEDED."""
        if not tx_created_at:
            return "UNKNOWN"

        now = current_time or datetime.now(timezone.utc)
        
        # Ensure timezone-aware comparisons
        if tx_created_at.tzinfo is None:
            tx_created_at = tx_created_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        elapsed_hours = (now - tx_created_at).total_seconds() / 3600.0
        max_hours = policy_record.get("max_tat_hours", 24)

        if elapsed_hours < max_hours:
            return "WITHIN_TAT"
        elif elapsed_hours == max_hours:
            return "TAT_REACHED"
        else:
            return "TAT_EXCEEDED"
