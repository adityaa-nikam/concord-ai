from app.services.action_gateway import ActionGateway, PolicyGate
from app.services.policy_service import PolicyService


def test_policy_gate_authorization():
    pol = PolicyService.retrieve_policy("DEBITED_BENEFICIARY_NOT_CREDITED")
    proposal = {
        "action": "INITIATE_REVERSAL",
        "transaction_id": "tx-001",
        "case_id": "case-001",
        "idempotency_key": "REVERSAL:tx-001",
        "reason_code": "ELIGIBLE_EXCEPTION",
        "payload": {}
    }

    res = PolicyGate.validate_action_proposal(proposal, pol, missing_evidence=[], is_already_resolved=False)
    assert res["passed"] is True


def test_action_gateway_idempotency_key(db_session):
    gateway = ActionGateway(db_session)
    proposal = {
        "action": "INITIATE_REVERSAL",
        "transaction_id": "tx-001",
        "case_id": "case-001",
        "idempotency_key": "REVERSAL:tx-001",
        "reason_code": "ELIGIBLE_EXCEPTION",
        "payload": {}
    }

    # First call -> Executes reversal
    first_res = gateway.execute_action_proposal(proposal)
    assert first_res["success"] is True
    assert first_res["status"] in ["SUCCESS", "ALREADY_COMPLETED"]

    # Second call with same idempotency key -> Returns cached result immediately
    second_res = gateway.execute_action_proposal(proposal)
    assert second_res["success"] is True
    assert second_res.get("already_executed_idempotent") is True
