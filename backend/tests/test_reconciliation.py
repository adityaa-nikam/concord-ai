from app.agents.understand import CustomerComplaintUnderstandEngine
from app.agents.reconcile import PaymentEvidenceReconciler


def test_understand_engine_extraction(db_session):
    text = "₹2,400 was deducted from my account, but the merchant/receiver did not receive the money."
    parsed = CustomerComplaintUnderstandEngine.parse_complaint(text, case_id="case-001", db=db_session)

    assert parsed["issue_type"] == "DEBITED_BENEFICIARY_NOT_CREDITED"
    assert parsed["extracted_amount"] == 2400.0
    assert parsed["extracted_intent"] == "FAILED_UPI_DISPUTE_REVERSAL"
    assert parsed["confidence"] >= 0.85


def test_reconcile_engine_uncredited_debit_conflict():
    tx_data = {"utr": "426189012345", "amount": 2400.0, "status": "PENDING"}
    gw_data = {"found": True, "gateway_status": "SUCCESS", "npci_status": "TIMEOUT"}
    ledger_data = {"found": True, "debit_status": "DEBITED"}
    bene_data = {"found": True, "credit_status": "NOT_CREDITED"}
    rev_data = {"found": True, "is_reversed": False}

    res = PaymentEvidenceReconciler.reconcile(tx_data, gw_data, ledger_data, bene_data, rev_data)

    assert res["evidence_summary"]["has_conflicts"] is True
    assert res["evidence_summary"]["primary_conflict"] == "DEBITED_BENEFICIARY_UNCREDITED"
    assert len(res["conflicts_detected"]) == 1
    assert res["conflicts_detected"][0]["severity"] == "HIGH"


def test_reconcile_engine_gateway_ledger_mismatch_conflict():
    tx_data = {"utr": "426189555666", "amount": 12000.0, "status": "PENDING"}
    gw_data = {"found": True, "gateway_status": "PENDING", "npci_status": "UNKNOWN"}
    ledger_data = {"found": True, "debit_status": "ON_HOLD"}
    bene_data = {"found": True, "credit_status": "NOT_CREDITED"}
    rev_data = {"found": True, "is_reversed": False}

    res = PaymentEvidenceReconciler.reconcile(tx_data, gw_data, ledger_data, bene_data, rev_data)

    assert res["evidence_summary"]["has_conflicts"] is True
    primary = res["evidence_summary"]["primary_conflict"]
    assert primary in ["GATEWAY_LEDGER_MISMATCH", "INCONSISTENT_BANK_HOLD"]
    assert any(c["severity"] in ["HIGH", "CRITICAL"] for c in res["conflicts_detected"])


def test_reconcile_engine_already_reversed():
    tx_data = {"utr": "426189098765", "amount": 1500.0, "status": "REVERSED"}
    gw_data = {"found": True, "gateway_status": "FAILED", "npci_status": "FAILED"}
    ledger_data = {"found": True, "debit_status": "REVERSED"}
    bene_data = {"found": True, "credit_status": "NOT_CREDITED"}
    rev_data = {"found": True, "is_reversed": True}

    res = PaymentEvidenceReconciler.reconcile(tx_data, gw_data, ledger_data, bene_data, rev_data)

    assert res["evidence_summary"]["is_reversed"] is True
    assert res["evidence_summary"]["primary_conflict"] == "REVERSAL_ALREADY_COMPLETED"
