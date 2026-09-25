from app.services import (
    PaymentGatewayService,
    BankLedgerService,
    BeneficiaryBankService,
    ReversalService
)
from app.models.enums import TransactionStatus


def test_payment_gateway_service(db_session):
    svc = PaymentGatewayService(db_session)
    tx_data = svc.get_transaction("tx-001")
    assert tx_data is not None
    assert tx_data["utr"] == "426189012345"

    gw_status = svc.get_payment_gateway_status("tx-001")
    assert gw_status["gateway_status"] == "SUCCESS"
    assert gw_status["npci_status"] == "TIMEOUT"


def test_bank_ledger_service(db_session):
    svc = BankLedgerService(db_session)
    ledger_status = svc.get_ledger_status("tx-001")
    assert ledger_status["debit_status"] == "DEBITED"
    assert ledger_status["account_debited"] is True


def test_beneficiary_service(db_session):
    svc = BeneficiaryBankService(db_session)
    bene_status = svc.get_beneficiary_status("tx-001")
    assert bene_status["credit_status"] == "NOT_CREDITED"
    assert bene_status["account_credited"] is False


def test_reversal_service_execution(db_session):
    svc = ReversalService(db_session)
    res = svc.initiate_reversal("tx-001", "case-001", "Test Reversal")
    assert res["success"] is True
    assert res["reversal_id"] == "REV-426189012345"
    assert res["amount"] == 2400.0

    # Verify idempotency
    res_again = svc.initiate_reversal("tx-001", "case-001", "Duplicate Reversal")
    assert res_again["success"] is True
    assert res_again.get("already_reversed") is True
