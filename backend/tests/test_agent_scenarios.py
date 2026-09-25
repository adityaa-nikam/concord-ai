from app.agents.runner import AgentRunner
from app.models.domain import Case
from app.models.enums import CaseStatus


def test_scenario_case_1_cross_system_conflict_act(db_session):
    """CASE-001: Gateway=SUCCESS, Ledger=DEBITED, Beneficiary=NOT_CREDITED -> Reconciled as CROSS_SYSTEM_CONFLICT -> ACT & RESOLVE."""
    runner = AgentRunner(db_session)
    run = runner.run_case_agent("case-001")

    assert run.status == "SUCCESS"
    assert run.steps_completed > 0

    case = db_session.query(Case).filter(Case.id == "case-001").first()
    assert case.status == CaseStatus.RESOLVED


def test_scenario_case_2_already_reversed(db_session):
    """CASE-002: Ledger=REVERSED -> Reconciled as ALREADY_RESOLVED -> NOTIFY_AND_CLOSE."""
    runner = AgentRunner(db_session)
    run = runner.run_case_agent("case-002")

    assert run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-002").first()
    assert case.status == CaseStatus.RESOLVED
    assert "reversal" in case.resolution_summary.lower()


def test_scenario_case_3_pending_within_tat_wait(db_session):
    """CASE-003: Gateway=PENDING, Ledger=PENDING -> Reconciled as PENDING_CONSISTENT -> WAIT & MONITOR."""
    runner = AgentRunner(db_session)
    run = runner.run_case_agent("case-003")

    assert run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-003").first()
    assert case.status == CaseStatus.INVESTIGATING
    assert "WAIT AND MONITOR" in case.resolution_summary


def test_scenario_case_4_ambiguous_bank_hold_escalate(db_session):
    """CASE-004: Ledger=ON_HOLD -> Reconciled as CROSS_SYSTEM_CONFLICT (INCONSISTENT_BANK_HOLD) -> ESCALATE TO OPS."""
    runner = AgentRunner(db_session)
    run = runner.run_case_agent("case-004")

    assert run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-004").first()
    assert case.status == CaseStatus.ESCALATED
    assert "ESCALATED" in case.resolution_summary


def test_scenario_case_5_verification_failure_escalate(db_session):
    """CASE-005: Reversal API triggered, but ledger stays DEBITED -> VERIFICATION_FAILED -> ESCALATE TO OPS."""
    runner = AgentRunner(db_session)
    run = runner.run_case_agent("case-005")

    assert run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-005").first()
    # Verification failure MUST NOT set case to RESOLVED; it must set case to ESCALATED!
    assert case.status == CaseStatus.ESCALATED
    assert "ESCALATED" in case.resolution_summary
