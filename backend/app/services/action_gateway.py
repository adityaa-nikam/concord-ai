from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.services.reversal import ReversalService

logger = logging.getLogger("tat_guardian.services.action_gateway")


class PolicyGate:
    """Safety validation gate that authorizes or rejects action proposals before execution."""

    @classmethod
    def validate_action_proposal(
        cls,
        proposal: Dict[str, Any],
        policy_record: Optional[Dict[str, Any]],
        missing_evidence: list,
        is_already_resolved: bool
    ) -> Dict[str, Any]:
        if is_already_resolved:
            return {
                "passed": False,
                "reason": "REJECTED_CASE_ALREADY_RESOLVED: Case is already marked resolved."
            }

        if not proposal or not proposal.get("transaction_id"):
            return {
                "passed": False,
                "reason": "REJECTED_MISSING_TRANSACTION_ID: Required transaction identifier missing."
            }

        if missing_evidence:
            return {
                "passed": False,
                "reason": f"REJECTED_MISSING_EVIDENCE: Cannot execute action due to missing evidence from {', '.join(missing_evidence)}."
            }

        allowlisted_actions = ["INITIATE_REVERSAL", "SEND_NOTIFICATION", "CREATE_ESCALATION", "WAIT_AND_MONITOR"]
        proposed_action = proposal.get("action")
        if proposed_action not in allowlisted_actions:
            return {
                "passed": False,
                "reason": f"UNAUTHORIZED_ACTION: Action '{proposed_action}' is not in the allowlisted action registry."
            }

        if policy_record and not policy_record.get("action_allowed", False):
            return {
                "passed": False,
                "reason": f"REJECTED_BY_POLICY: Policy {policy_record.get('policy_id')} disallows financial mutation."
            }

        return {
            "passed": True,
            "reason": "POLICY_GATE_AUTHORIZED"
        }


class ActionGateway:
    """Controlled Action Gateway enforcing idempotency keys (REVERSAL:{transaction_id})."""

    _idempotency_registry: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def clear_registry(cls):
        cls._idempotency_registry.clear()

    def __init__(self, db: Session):
        self.db = db
        self.reversal_svc = ReversalService(db)

    def execute_action_proposal(self, proposal: Dict[str, Any]) -> Dict[str, Any]:
        key = proposal.get("idempotency_key") or f"REVERSAL:{proposal.get('transaction_id')}"

        # Idempotency Lock Check
        if key in self._idempotency_registry:
            logger.info(f"[ACTION GATEWAY] Idempotency key {key} hit! Returning cached execution result.")
            existing = dict(self._idempotency_registry[key])
            existing["already_executed_idempotent"] = True
            return existing

        action_name = proposal.get("action")
        tx_id = proposal.get("transaction_id")
        case_id = proposal.get("case_id")
        reason = proposal.get("reason_code", "Action Gateway Trigger")

        if action_name == "INITIATE_REVERSAL":
            result = self.reversal_svc.initiate_reversal(
                transaction_id=tx_id,
                case_id=case_id,
                reason=reason
            )
            # Store in idempotency registry
            self._idempotency_registry[key] = result
            return result
        else:
            return {
                "success": False,
                "error": f"Unsupported action gateway action: {action_name}"
            }
