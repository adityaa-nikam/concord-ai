from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from app.models.domain import Transaction

logger = logging.getLogger("tat_guardian.services.beneficiary")


class BeneficiaryBankService:
    """Mock Beneficiary Bank status check service (SBI, HDFC, ICICI, etc.)."""

    def __init__(self, db: Session):
        self.db = db

    def get_beneficiary_status(self, transaction_id: str) -> Dict[str, Any]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return {
                "found": False,
                "error": f"Transaction {transaction_id} not found in Beneficiary Bank switch"
            }
        
        is_credited = (tx.beneficiary_credit_status == "CREDITED")
        return {
            "found": True,
            "transaction_id": tx.id,
            "utr": tx.utr,
            "beneficiary_bank": tx.beneficiary_bank,
            "payee_upi": tx.payee_upi,
            "credit_status": tx.beneficiary_credit_status,
            "account_credited": is_credited,
            "response_code": "00" if is_credited else "U69",
            "response_message": "SUCCESS" if is_credited else "BENEFICIARY_CBS_OFFLINE"
        }
