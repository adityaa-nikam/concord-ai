import uuid
from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.models.domain import Case, Action, AuditLog
from app.models.enums import CaseStatus, ActionStatus, ActionType

logger = logging.getLogger("tat_guardian.services.escalation")


class EscalationService:
    """Mock Human Ops Escalation service producing structured evidence packets."""

    def __init__(self, db: Session):
        self.db = db

    def create_human_escalation(
        self,
        case_id: str,
        reason: str,
        details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            return {"success": False, "error": f"Case {case_id} not found"}

        case.status = CaseStatus.ESCALATED
        case.resolution_summary = f"ESCALATED TO HUMAN OPS: {reason}"

        # Structured evidence packet format
        escalation_packet = {
            "case_id": case.id,
            "case_number": case.case_number,
            "reason": reason,
            "evidence": details.get("evidence_summary") if details else {},
            "conflicts": details.get("conflicts_detected") if details else [],
            "policy": details.get("policy_context") if details else {},
            "recommended_next_step": details.get("recommended_next_step") or "Investigate gateway-ledger reconciliation."
        }

        action_id = str(uuid.uuid4())
        action = Action(
            id=action_id,
            case_id=case_id,
            action_type=ActionType.ESCALATION,
            status=ActionStatus.SUCCESS,
            initiated_by="CONCORD_AI",
            payload={"reason": reason, "details": details},
            result_payload=escalation_packet
        )
        self.db.add(action)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_type="ESCALATED",
            actor="CONCORD_AI",
            details=escalation_packet
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"Case {case.case_number} escalated with evidence packet: {reason}")
        return {
            "success": True,
            "escalation_id": action_id,
            "case_number": case.case_number,
            "status": "ESCALATED",
            "queue": "HUMAN_OPS_TIER_2",
            "reason": reason,
            "escalation_packet": escalation_packet
        }
