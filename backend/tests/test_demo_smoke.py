import pytest
from app.demo.orchestrator import DemoOrchestrator
from app.models.domain import Case, CaseStatus, Action


def test_demo_health_check(db_session):
    """Verify demo health endpoint returns READY status with component health."""
    health = DemoOrchestrator.get_demo_health(db_session)
    assert health["status"] == "READY"
    assert health["components"]["database"] == "HEALTHY"
    assert health["components"]["policies_loaded"] >= 5
    assert health["components"]["agent_graph"] == "COMPILED"


def test_demo_reset_environment(db_session):
    """Verify demo reset restores baseline synthetic cases and transaction states."""
    res = DemoOrchestrator.reset_demo_environment(db_session)
    assert res["success"] is True
    assert res["reset_cases_count"] == 5

    case = db_session.query(Case).filter(Case.id == "case-001").first()
    assert case is not None
    assert case.status == CaseStatus.NEW


def test_demo_scenario_1_conflicting_payment(db_session):
    """Demo Scenario 1: Conflicting Payment -> Reconciles CROSS_SYSTEM_CONFLICT -> Reversal & Verification -> RESOLVED."""
    result = DemoOrchestrator.run_demo_scenario("1", db_session)
    assert result["status"] == "SUCCESS"
    assert result["final_case_status"] == "RESOLVED"
    assert result["duration_ms"] > 0
    assert result["steps_completed"] > 0


def test_demo_scenario_2_already_resolved(db_session):
    """Demo Scenario 2: Already Resolved -> Detects prior reversal -> NO duplicate action -> RESOLVED."""
    result = DemoOrchestrator.run_demo_scenario("2", db_session)
    assert result["status"] == "SUCCESS"
    assert result["final_case_status"] == "RESOLVED"

    # Verify no new reversal action was triggered
    actions = db_session.query(Action).filter(Action.case_id == "case-002").all()
    assert len(actions) == 0


def test_demo_scenario_3_pending_within_tat(db_session):
    """Demo Scenario 3: Pending within TAT -> Reconciles PENDING_CONSISTENT -> WAIT AND MONITOR."""
    result = DemoOrchestrator.run_demo_scenario("3", db_session)
    assert result["status"] == "SUCCESS"
    assert result["final_case_status"] == "INVESTIGATING"
    assert "WAIT AND MONITOR" in result["resolution_summary"]


def test_demo_scenario_4_verification_failure(db_session):
    """Demo Scenario 4: Reversal API succeeds, but ledger stays DEBITED -> VERIFICATION_FAILED -> ESCALATED."""
    result = DemoOrchestrator.run_demo_scenario("4", db_session)
    assert result["status"] == "SUCCESS"
    assert result["final_case_status"] == "ESCALATED"
    assert "ESCALATED" in result["resolution_summary"]


def test_demo_scenario_5_unresolved_conflict(db_session):
    """Demo Scenario 5: High Value / Administrative Hold -> Policy Threshold -> ESCALATED."""
    result = DemoOrchestrator.run_demo_scenario("5", db_session)
    assert result["status"] == "SUCCESS"
    assert result["final_case_status"] == "ESCALATED"
