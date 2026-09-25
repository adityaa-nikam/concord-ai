import pytest
from app.schemas.evidence import EvidenceReliability, EvidenceFreshness
from app.services.evidence_service import EvidenceNormalizationService
from app.services.policy_rag_service import PolicyRAGService
from app.agents.reasoning import ResolutionReasoningEngine
from app.agents.reconcile import PaymentEvidenceReconciler


def test_evidence_aggregator_normalization():
    tx_data = {"amount": 2400.0, "status": "PENDING", "utr": "426189012345"}
    gw_data = {"found": True, "gateway_status": "SUCCESS", "npci_status": "TIMEOUT"}
    ledger_data = {"found": True, "debit_status": "DEBITED"}
    bene_data = {"found": True, "credit_status": "NOT_CREDITED"}
    rev_data = {"found": True, "is_reversed": False}
    msg = "₹2,400 deducted from my account but receiver did not get money."

    bundle = EvidenceNormalizationService.normalize_evidence_set(
        tx_data=tx_data,
        gw_data=gw_data,
        ledger_data=ledger_data,
        bene_data=bene_data,
        rev_data=rev_data,
        customer_msg=msg,
        extracted_amount=2400.0
    )

    assert len(bundle.items) >= 7
    assert bundle.system_of_record_count >= 4
    assert bundle.unverified_claim_count == 2
    assert len(bundle.missing_fields) == 0

    ledger_item = next(i for i in bundle.items if i.source == "ledger")
    assert ledger_item.reliability == EvidenceReliability.SYSTEM_OF_RECORD
    assert ledger_item.freshness == EvidenceFreshness.CURRENT
    assert ledger_item.value == "DEBITED"



def test_policy_rag_service_retrieval_and_fact_preservation():
    # 1. Standard Conflict Retrieval
    matches = PolicyRAGService.retrieve_applicable_policies(
        issue_type="DEBITED_BENEFICIARY_NOT_CREDITED",
        reconciled_case="CROSS_SYSTEM_CONFLICT",
        amount=2400.0,
        debit_status="DEBITED",
        credit_status="NOT_CREDITED"
    )

    assert len(matches) > 0
    top = matches[0]
    assert top.policy_id == "POL-NPCI-T1-AUTOREVERSAL"
    assert top.auto_execution_allowed is True
    assert "INITIATE_REVERSAL" in top.permitted_actions

    # 2. Fact Preservation Safeguard Check (Already reversed)
    fact_val = PolicyRAGService.validate_policy_against_facts(
        top,
        {"is_reversed": True, "amount": 2400.0}
    )
    assert fact_val["valid"] is False
    assert "FACT CONSTRAINED" in fact_val["reason"]


def test_resolution_reasoning_engine_decision_grounding():
    # Scenario A: Standard Auto-Reversal
    policy_matches = PolicyRAGService.retrieve_applicable_policies(
        issue_type="DEBITED_BENEFICIARY_NOT_CREDITED",
        reconciled_case="CROSS_SYSTEM_CONFLICT",
        amount=2400.0,
        debit_status="DEBITED",
        credit_status="NOT_CREDITED"
    )

    assessment = ResolutionReasoningEngine.evaluate_resolution(
        reconciled_case="CROSS_SYSTEM_CONFLICT",
        evidence_summary={"debit_status": "DEBITED", "credit_status": "NOT_CREDITED", "gateway_status": "SUCCESS", "is_reversed": False, "amount": 2400.0},
        conflicts=[{"conflict_type": "DEBITED_BENEFICIARY_UNCREDITED"}],
        missing_evidence=[],
        policy_matches=policy_matches,
        nlu_confidence=0.95,
        tx_id="tx-100"
    )

    assert assessment.decision == "ACT"
    assert assessment.proposed_action == "INITIATE_REVERSAL"
    assert assessment.confidence_score >= 0.85
    assert assessment.idempotency_key == "REVERSAL:tx-100"
    assert "Remitter ledger status is 'DEBITED'" in assessment.reasoning_summary.facts_grounding
    assert "NPCI T+1" in assessment.reasoning_summary.policy_grounding
    assert "Idempotency Key locked" in assessment.reasoning_summary.safety_and_idempotency


def test_high_value_risk_threshold_escalation():
    # Transaction > ₹50,000 must trigger High Value Risk Safeguard
    policy_matches = PolicyRAGService.retrieve_applicable_policies(
        issue_type="DEBITED_BENEFICIARY_NOT_CREDITED",
        reconciled_case="CROSS_SYSTEM_CONFLICT",
        amount=75000.0,
        debit_status="DEBITED",
        credit_status="NOT_CREDITED"
    )

    assessment = ResolutionReasoningEngine.evaluate_resolution(
        reconciled_case="CROSS_SYSTEM_CONFLICT",
        evidence_summary={"debit_status": "DEBITED", "credit_status": "NOT_CREDITED", "gateway_status": "SUCCESS", "is_reversed": False, "amount": 75000.0},
        conflicts=[{"conflict_type": "DEBITED_BENEFICIARY_UNCREDITED"}],
        missing_evidence=[],
        policy_matches=policy_matches,
        nlu_confidence=0.95,
        tx_id="tx-large"
    )

    assert assessment.decision == "ESCALATE"
    assert assessment.proposed_action == "CREATE_ESCALATION"
    assert assessment.requires_human_override is True
    assert "exceeds automated safety limit ₹50,000" in assessment.reasoning_summary.policy_grounding
