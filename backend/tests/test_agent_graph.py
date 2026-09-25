from app.agents.runner import AgentRunner
from app.models.domain import Case
from app.models.enums import CaseStatus


def test_agent_execution_case_a_reversal_path(db_session):
    """Case A (case-001): Money deducted, receiver not credited -> Auto Reversal & Resolve."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-001")

    assert agent_run.status == "SUCCESS"
    assert agent_run.steps_completed >= 5

    case = db_session.query(Case).filter(Case.id == "case-001").first()
    assert case.status == CaseStatus.RESOLVED


def test_agent_execution_case_b_already_reversed(db_session):
    """Case B (case-002): Money deducted, reversal already completed prior -> Notify & Resolve."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-002")

    assert agent_run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-002").first()
    assert case.status == CaseStatus.RESOLVED


def test_agent_execution_case_c_escalation_path(db_session):
    """Case C (case-004): Inconsistent/Pending bank hold state -> Escalated with Escalation Packet."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-004")

    assert agent_run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-004").first()
    assert case.status == CaseStatus.ESCALATED


def test_agent_execution_case_d_wait_and_monitor(db_session):
    """Case D (case-003): Pending transaction within NPCI clearing window -> Wait & Monitor."""
    runner = AgentRunner(db_session)
    agent_run = runner.run_case_agent("case-003")

    assert agent_run.status == "SUCCESS"

    case = db_session.query(Case).filter(Case.id == "case-003").first()
    assert case.status == CaseStatus.INVESTIGATING
