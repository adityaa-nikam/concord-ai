from datetime import datetime, timedelta, timezone
from app.services.policy_service import PolicyService, TATEvaluator
from app.policies.tat_policy import TATPolicyEngine


def test_policy_retrieval():
    pol = PolicyService.retrieve_policy("DEBITED_BENEFICIARY_NOT_CREDITED")
    assert pol["policy_id"] == "UPI_TRANSFER_DEBITED_NOT_CREDITED"
    assert pol["action_allowed"] is True
    assert pol["requires_verification"] is True


def test_tat_evaluator_clock_injection():
    tx_time = datetime(2026, 9, 24, 10, 0, 0, tzinfo=timezone.utc)
    
    # 2 hours later -> WITHIN_TAT (max 24 hrs)
    current_within = datetime(2026, 9, 24, 12, 0, 0, tzinfo=timezone.utc)
    pol = PolicyService.retrieve_policy("DEBITED_BENEFICIARY_NOT_CREDITED")
    
    status_within = TATEvaluator.evaluate_tat(tx_time, pol, current_time=current_within)
    assert status_within == "WITHIN_TAT"

    # 30 hours later -> TAT_EXCEEDED
    current_exceeded = datetime(2026, 9, 25, 16, 0, 0, tzinfo=timezone.utc)
    status_exceeded = TATEvaluator.evaluate_tat(tx_time, pol, current_time=current_exceeded)
    assert status_exceeded == "TAT_EXCEEDED"
