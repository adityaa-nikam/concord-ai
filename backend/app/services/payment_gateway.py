from typing import Dict, Any, Optional
import logging
from sqlalchemy.orm import Session
from app.models.domain import Transaction

logger = logging.getLogger("tat_guardian.services.gateway")


class PaymentGatewayService:
    """Mock Payment Gateway service simulating Paytm PG & NPCI Clearing House responses."""

    def __init__(self, db: Session):
        self.db = db

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return None
        return {
            "transaction_id": tx.id,
            "utr": tx.utr,
            "amount": tx.amount,
            "payer_upi": tx.payer_upi,
            "payee_upi": tx.payee_upi,
            "status": tx.status.value if hasattr(tx.status, 'value') else tx.status,
            "failure_reason": tx.failure_reason,
            "created_at": tx.created_at.isoformat()
        }

    def get_payment_gateway_status(self, transaction_id: str) -> Dict[str, Any]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return {
                "found": False,
                "error": f"Transaction {transaction_id} not found in Gateway records"
            }
        
        return {
            "found": True,
            "transaction_id": tx.id,
            "utr": tx.utr,
            "gateway_status": tx.gateway_status,
            "npci_status": tx.npci_status,
            "switch_response_code": "00" if tx.gateway_status == "SUCCESS" else "U19",
            "switch_response_message": "APPROVED" if tx.gateway_status == "SUCCESS" else "NPCI TIMEOUT"
        }
