from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from app.models.domain import Transaction

logger = logging.getLogger("tat_guardian.services.ledger")


class BankLedgerService:
    """Mock Core Banking System (CBS) Ledger service for Remitter Bank."""

    def __init__(self, db: Session):
        self.db = db

    def get_ledger_status(self, transaction_id: str) -> Dict[str, Any]:
        tx = self.db.query(Transaction).filter(
            (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
        ).first()
        if not tx:
            return {
                "found": False,
                "error": f"Transaction {transaction_id} not found in Core Banking Ledger"
            }
        
        return {
            "found": True,
            "transaction_id": tx.id,
            "utr": tx.utr,
            "remitter_bank": tx.remitter_bank,
            "debit_status": tx.remitter_debit_status,
            "amount": tx.amount,
            "account_debited": True if tx.remitter_debit_status == "DEBITED" else False,
            "hold_reference": f"HOLD-{tx.utr[-6:]}" if tx.remitter_debit_status == "ON_HOLD" else None
        }
