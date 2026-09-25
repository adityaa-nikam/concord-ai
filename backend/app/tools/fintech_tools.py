from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from app.services import (
    PaymentGatewayService,
    BankLedgerService,
    BeneficiaryBankService,
    ReversalService,
    NotificationService,
    EscalationService
)


class FintechTools:
    """Standardized tool wrapper for autonomous agent execution."""

    def __init__(self, db: Session):
        self.db = db
        self.gateway_svc = PaymentGatewayService(db)
        self.ledger_svc = BankLedgerService(db)
        self.beneficiary_svc = BeneficiaryBankService(db)
        self.reversal_svc = ReversalService(db)
        self.notification_svc = NotificationService(db)
        self.escalation_svc = EscalationService(db)

    def get_transaction(self, transaction_id: str) -> Dict[str, Any]:
        res = self.gateway_svc.get_transaction(transaction_id)
        if not res:
            return {"found": False, "error": f"Transaction {transaction_id} not found"}
        return res

    def get_payment_gateway_status(self, transaction_id: str) -> Dict[str, Any]:
        return self.gateway_svc.get_payment_gateway_status(transaction_id)

    def get_ledger_status(self, transaction_id: str) -> Dict[str, Any]:
        return self.ledger_svc.get_ledger_status(transaction_id)

    def get_beneficiary_status(self, transaction_id: str) -> Dict[str, Any]:
        return self.beneficiary_svc.get_beneficiary_status(transaction_id)

    def get_reversal_status(self, transaction_id: str) -> Dict[str, Any]:
        return self.reversal_svc.get_reversal_status(transaction_id)

    def initiate_reversal(self, transaction_id: str, case_id: str, reason: str) -> Dict[str, Any]:
        return self.reversal_svc.initiate_reversal(transaction_id, case_id, reason)

    def send_customer_notification(self, customer_id: str, case_id: str, message: str) -> Dict[str, Any]:
        return self.notification_svc.send_customer_notification(customer_id, case_id, message)

    def create_human_escalation(self, case_id: str, reason: str, details: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        return self.escalation_svc.create_human_escalation(case_id, reason, details)
