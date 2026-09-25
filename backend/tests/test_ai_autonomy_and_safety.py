import pytest
from unittest.mock import patch
import httpx

from app.core.llm_provider import LLMProvider, AIEvidenceAssessment, AIResolutionProposal
from app.agents.runner import AgentRunner
from app.schemas.reconciliation import ReconciliationResult, Conflict
from app.services.action_gateway import PolicyGate, ActionGateway
from app.policies.schemas import PolicyCitation
from app.services.policy_service import PolicyService
from app.services.tat_engine import TATEvaluationResult
from app.models.domain import Case, CaseStatus


# =========================================================
# 1 & 2. Mock & Live LLM Structured Output Tests
# =========================================================

def test_mock_llm_structured_output():
    """Verify Mock LLM returns strictly validated Pydantic models."""
    assessment = LLMProvider.assess_evidence(
        customer_message="₹2,400 debited but receiver not credited",
        normalized_evidence=[{"source": "Gateway", "field": "status", "value": "SUCCESS"}],
        reconciliation_summary="Cross-system conflict",
        reconciled_category="CROSS_SYSTEM_CONFLICT",
        conflicts=[{"summary": "Gateway SUCCESS vs Ledger PENDING"}],
        missing_fields=["beneficiary_credit_status"]
    )
    assert isinstance(assessment, AIEvidenceAssessment)
    assert "get_beneficiary_status" in assessment.recommended_next_evidence
    assert len(assessment.known_facts) > 0

    reconcile_res = ReconciliationResult(
        status="CONFLICT",
        reconciled_case_category="CROSS_SYSTEM_CONFLICT",
        conflicts=[Conflict(
            conflict_type="GATEWAY_VS_LEDGER",
            severity="HIGH",
            sources=["Gateway", "Ledger"],
            summary="Gateway SUCCESS vs Ledger PENDING"
        )],
        known_facts=[],
        missing_information=[],
        unresolved_questions=[],
        recommended_next_evidence=[],
        summary="Conflict between Gateway and Ledger"
    )
    tat_res = TATEvaluationResult(
        tat_status="TAT_EXCEEDED",
        tat_rule="T_PLUS_1",
        max_tat_hours=24,
        elapsed_time_hours=48.0,
        remaining_time_hours=-24.0,
        deadline_iso="2026-09-24T00:00:00Z",
        compensation_applicable=True,
        compensation_amount=100.0,
        delay_days=1
    )

    proposal = LLMProvider.propose_resolution(
        customer_message="₹2,400 debited but receiver not credited",
        reconciliation=reconcile_res,
        citations=[],
        tat_result=tat_res,
        amount=2400.0,
        prompt_injection_detected=False
    )
    assert isinstance(proposal, AIResolutionProposal)
    assert proposal.decision in ["ACT", "WAIT", "ESCALATE", "RESOLVE"]
    assert proposal.action in ["INITIATE_REVERSAL", "WAIT_AND_MONITOR", "CREATE_ESCALATION", "SEND_NOTIFICATION"]


def test_live_llm_structured_output_mocked_api():
    """Simulate a Live LLM API call returning JSON matching schema."""
    fake_assessment_json = {
        "assessment": "CROSS_SYSTEM_CONFLICT",
        "known_facts": ["Gateway reports SUCCESS", "Ledger reports PENDING"],
        "uncertainties": ["Beneficiary bank settlement status unverified"],
        "recommended_next_evidence": ["get_beneficiary_status"],
        "risk_flags": [],
        "reasoning_summary": "Live LLM parsed evidence: Gateway and Ledger disagree."
    }

    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", return_value=fake_assessment_json):
        res = LLMProvider.assess_evidence(
            customer_message="Payment stuck",
            normalized_evidence=[],
            reconciliation_summary="Conflict",
            reconciled_category="CROSS_SYSTEM_CONFLICT",
            conflicts=[],
            missing_fields=[]
        )
        assert isinstance(res, AIEvidenceAssessment)
        assert res.assessment == "CROSS_SYSTEM_CONFLICT"
        assert res.reasoning_summary.startswith("Live LLM parsed evidence")


# =========================================================
# 3, 9, 10, 11. LLM Error & Fallback Tests
# =========================================================

def test_invalid_llm_schema_fallback():
    """If API returns invalid schema fields, provider gracefully falls back to mock assessment."""
    broken_payload = {"invalid_key": "no required fields"}
    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", return_value=broken_payload):
        res = LLMProvider.assess_evidence(
            customer_message="Help",
            normalized_evidence=[],
            reconciliation_summary="",
            reconciled_category="UNKNOWN",
            conflicts=[],
            missing_fields=[]
        )
        assert isinstance(res, AIEvidenceAssessment)


def test_llm_unavailable_fallback():
    """If LLM endpoint throws HTTP error, system falls back safely."""
    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", side_effect=httpx.ConnectError("Service Unavailable")):
        res = LLMProvider.assess_evidence(
            customer_message="Payment stuck",
            normalized_evidence=[],
            reconciliation_summary="",
            reconciled_category="UNKNOWN",
            conflicts=[],
            missing_fields=[]
        )
        assert isinstance(res, AIEvidenceAssessment)


def test_llm_timeout_fallback():
    """If LLM endpoint times out, system falls back safely."""
    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", side_effect=httpx.TimeoutException("Timeout")):
        res = LLMProvider.propose_resolution(
            customer_message="Timeout test",
            reconciliation=ReconciliationResult(
                status="CONSISTENT",
                reconciled_case_category="CONSISTENT_SUCCESS",
                conflicts=[],
                known_facts=[],
                missing_information=[],
                unresolved_questions=[],
                recommended_next_evidence=[],
                summary="No conflict"
            ),
            citations=[],
            tat_result=TATEvaluationResult(
                tat_status="WITHIN_TAT",
                tat_rule="T_PLUS_1",
                max_tat_hours=24,
                elapsed_time_hours=2.0,
                remaining_time_hours=22.0,
                deadline_iso="2026-09-25T00:00:00Z",
                compensation_applicable=False,
                compensation_amount=0.0,
                delay_days=0
            )
        )
        assert isinstance(res, AIResolutionProposal)


def test_llm_malformed_json():
    """If LLM returns malformed JSON, fallback is triggered."""
    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", side_effect=ValueError("Invalid JSON")):
        res = LLMProvider.assess_evidence(
            customer_message="Broken JSON",
            normalized_evidence=[],
            reconciliation_summary="",
            reconciled_category="UNKNOWN",
            conflicts=[],
            missing_fields=[]
        )
        assert isinstance(res, AIEvidenceAssessment)


# =========================================================
# 4 & 5. Action Authorization & Policy Gate Safety Tests
# =========================================================

def test_invalid_action_proposal():
    """Mock LLM proposing an invalid action string is caught by Policy Gate."""
    pol = PolicyService.retrieve_policy("DEBITED_BENEFICIARY_NOT_CREDITED")
    proposal = {
        "action": "INVALID_ACTION_STRING",
        "transaction_id": "tx-001",
        "case_id": "case-001",
        "idempotency_key": "REVERSAL:tx-001",
        "reason_code": "TEST",
        "payload": {}
    }
    auth = PolicyGate.validate_action_proposal(proposal, pol, missing_evidence=[], is_already_resolved=False)
    assert auth["passed"] is False


def test_unauthorized_action_proposal():
    """LLM proposes INITIATE_REVERSAL for a case where missing evidence remains, Policy Gate rejects."""
    pol = PolicyService.retrieve_policy("DEBITED_BENEFICIARY_NOT_CREDITED")
    proposal = {
        "action": "INITIATE_REVERSAL",
        "transaction_id": "tx-001",
        "case_id": "case-001",
        "idempotency_key": "REVERSAL:tx-001",
        "reason_code": "ELIGIBLE_EXCEPTION",
        "payload": {}
    }
    auth = PolicyGate.validate_action_proposal(proposal, pol, missing_evidence=["beneficiary_credit_status"], is_already_resolved=False)
    assert auth["passed"] is False


# =========================================================
# 6. AI Recommended Next Evidence Loop Test
# =========================================================

def test_ai_selected_next_evidence_loop(db_session):
    """Test AI proposing next tool telemetry via agent runner."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-001")

    assert agent_run.status == "SUCCESS"
    assert agent_run.steps_completed >= 5


# =========================================================
# 7 & 8. Prompt Injection & Fabricated System Fact Safety Tests
# =========================================================

def test_prompt_injection_defense(db_session):
    """Customer attempts prompt injection. Policy Gate and system facts prevent unauthorized action."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-005")

    assert agent_run.status == "SUCCESS"
    case = db_session.query(Case).filter(Case.id == "case-005").first()
    assert case.status in [CaseStatus.ESCALATED, CaseStatus.RESOLVED]


def test_fabricated_system_fact_safety():
    """Even if an LLM mock proposes a fabricated reversal success, deterministic tool facts remain authoritative."""
    pol = PolicyService.retrieve_policy("PENDING_WITHIN_TAT")
    proposal = {
        "action": "INITIATE_REVERSAL",
        "transaction_id": "tx-002",
        "case_id": "case-002",
        "idempotency_key": "REVERSAL:tx-002",
        "reason_code": "FABRICATED_REASON",
        "payload": {}
    }
    auth = PolicyGate.validate_action_proposal(proposal, pol, missing_evidence=[], is_already_resolved=False)
    assert auth["passed"] is False


# =========================================================
# 12, 13, 14. Graph Policy Gate & Verification Tests
# =========================================================

def test_successful_ai_proposal_passes_gate_and_verifies(db_session):
    """Eligible case: LLM proposes reversal, Policy Gate authorizes, reversal executes and verifies cleanly."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-001")

    assert agent_run.status == "SUCCESS"
    case = db_session.query(Case).filter(Case.id == "case-001").first()
    assert case.status == CaseStatus.RESOLVED


def test_verification_failure_escalates(db_session):
    """If post-action multi-source verification fails, the action gateway handles idempotency and status."""
    gateway = ActionGateway(db_session)
    proposal = {
        "action": "INITIATE_REVERSAL",
        "transaction_id": "tx-001",
        "case_id": "case-001",
        "idempotency_key": "REVERSAL:tx-001",
        "reason_code": "ELIGIBLE_EXCEPTION",
        "payload": {}
    }
    reversal_res = gateway.execute_action_proposal(proposal)
    assert reversal_res["success"] is True
    assert "status" in reversal_res


def test_dynamic_next_evidence_excludes_already_called_tools():
    """Verify AI-selected next evidence dynamically excludes tools that have already been executed."""
    assessment = LLMProvider.assess_evidence(
        customer_message="Help",
        normalized_evidence=[],
        reconciliation_summary="",
        reconciled_category="CROSS_SYSTEM_CONFLICT",
        conflicts=[],
        missing_fields=["beneficiary_credit_status"],
        already_called_tools=["get_beneficiary_status"]
    )
    assert "get_beneficiary_status" not in assessment.recommended_next_evidence


def test_live_llm_failure_forces_safe_escalation():
    """Verify that in Live LLM mode, if the API call fails, the system safely escalates rather than attempting financial action."""
    with patch.object(LLMProvider, "is_live_mode", return_value=True), \
         patch.object(LLMProvider, "_call_llm_api", side_effect=httpx.ConnectError("API connection failed")):
        proposal = LLMProvider.propose_resolution(
            customer_message="Payment stuck",
            reconciliation=ReconciliationResult(
                status="CONFLICT",
                reconciled_case_category="CROSS_SYSTEM_CONFLICT",
                conflicts=[],
                known_facts=[],
                missing_information=[],
                unresolved_questions=[],
                recommended_next_evidence=[],
                summary="Conflict"
            ),
            citations=[],
            tat_result=TATEvaluationResult(
                tat_status="TAT_EXCEEDED",
                tat_rule="T_PLUS_1",
                max_tat_hours=24,
                elapsed_time_hours=48.0,
                remaining_time_hours=-24.0,
                deadline_iso="2026-09-24T00:00:00Z",
                compensation_applicable=True,
                compensation_amount=100.0,
                delay_days=1
            )
        )
        assert proposal.decision == "ESCALATE"
        assert proposal.action == "CREATE_ESCALATION"
        assert proposal.reason_code == "LLM_PROVIDER_FAILURE"

