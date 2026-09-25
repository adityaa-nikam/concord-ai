import uuid
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from app.models.domain import Transaction, Action, AuditLog, Case
from app.models.enums import TransactionStatus, ActionStatus, ActionType, CaseStatus

logger = logging.getLogger("tat_guardian.services.reversal")


class ReversalService:
    """Mock Auto-Reversal processing engine for UPI transactions with structured responses."""

    def __init__(self, db: Session):
        self.db = db

    def get_reversal_status(self, transaction_id: str) -> Dict[str, Any]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return {"found": False, "error": "Transaction not found"}
        
        is_reversed = (tx.status == TransactionStatus.REVERSED)
        return {
            "found": True,
            "transaction_id": tx.id,
            "utr": tx.utr,
            "is_reversed": is_reversed,
            "status": tx.status.value if hasattr(tx.status, 'value') else tx.status,
            "reversal_reference": f"REV-{tx.utr}" if is_reversed else None
        }

    def initiate_reversal(self, transaction_id: str, case_id: str, reason: str, initiated_by: str = "CONCORD_AI") -> Dict[str, Any]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return {
                "success": False,
                "status": "REJECTED",
                "transaction_id": transaction_id,
                "action": "INITIATE_REVERSAL",
                "error": f"Transaction {transaction_id} not found"
            }

        case = self.db.query(Case).filter(Case.id == case_id).first()

        # Idempotency check: if already reversed
        if tx.status == TransactionStatus.REVERSED:
            return {
                "success": True,
                "status": "ALREADY_COMPLETED",
                "already_reversed": True,
                "transaction_id": tx.id,
                "action": "INITIATE_REVERSAL",
                "reversal_id": f"REV-{tx.utr}",
                "reference_id": f"REV-{tx.utr}",
                "amount": tx.amount,
                "message": "Transaction was already reversed previously"
            }

        reversal_ref = f"REV-{tx.utr}"

        # Execute reversal mutation on mock transaction
        # NOTE: Do NOT set case.status = RESOLVED here! Workflow MUST proceed to verification.
        if tx.failure_reason == "SIMULATED_LEDGER_LOCK":
            tx.status = TransactionStatus.FAILED
            tx.remitter_debit_status = "DEBITED"
        else:
            tx.status = TransactionStatus.REVERSED
            tx.remitter_debit_status = "REVERSED"
        
        if case:
            case.status = CaseStatus.ACTION_IN_PROGRESS

        # Record controlled action
        action = Action(
            id=str(uuid.uuid4()),
            case_id=case_id,
            action_type=ActionType.REVERSAL,
            status=ActionStatus.SUCCESS,
            initiated_by=initiated_by,
            payload={"transaction_id": tx.id, "reason": reason, "amount": tx.amount},
            result_payload={"reversal_reference": reversal_ref, "credited_to": tx.payer_upi}
        )
        self.db.add(action)

        # Audit log
        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_type="ACTION_EXECUTED",
            actor=initiated_by,
            details={"action": "INITIATE_REVERSAL", "reversal_ref": reversal_ref, "amount": tx.amount, "reason": reason}
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"Auto-reversal executed for tx {tx.utr}: Ref {reversal_ref}")
        return {
            "success": True,
            "status": "SUCCESS",
            "transaction_id": tx.id,
            "action": "INITIATE_REVERSAL",
            "reversal_id": reversal_ref,
            "reference_id": reversal_ref,
            "amount": tx.amount,
            "payer_upi": tx.payer_upi,
            "message": f"Successfully initiated reversal of ₹{tx.amount} to {tx.payer_upi}"
        }
