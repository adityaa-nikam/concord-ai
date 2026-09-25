import uuid
from datetime import datetime, timezone
import logging
from sqlalchemy.orm import Session
from app.models.domain import Case, AgentRun, ToolCall, AuditLog, CaseStatus
from app.agents.state import CaseAgentState
from app.agents.graph import build_tat_agent_graph

logger = logging.getLogger("tat_guardian.agents.runner")


class AgentRunner:
    """Executes LangGraph agent runs and persists state, tool calls, and audit logs to DB."""

    def __init__(self, db: Session):
        self.db = db

    def run_case_agent(self, case_id: str) -> AgentRun:
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case {case_id} not found")

        run_id = str(uuid.uuid4())
        agent_run = AgentRun(
            id=run_id,
            case_id=case_id,
            status="RUNNING",
            steps_completed=0,
            started_at=datetime.now(timezone.utc)
        )
        self.db.add(agent_run)
        self.db.commit()

        initial_state: CaseAgentState = {
            "case_id": case.id,
            "case_number": case.case_number,
            "customer_id": case.customer_id,
            "transaction_id": case.transaction_id,
            "utr": case.transaction.utr if case.transaction else "",
            "customer_message": case.issue_description,
            "issue_description": case.issue_description,
            
            # Understand
            "extracted_intent": None,
            "extracted_amount": None,
            "extracted_transaction_id": None,
            "issue_type": None,
            "understanding_confidence": 0.0,
            "is_utr_ambiguous": False,
            "prompt_injection_detected": False,


            # Diagnostic stores
            "transaction_data": None,
            "gateway_data": None,
            "ledger_data": None,
            "beneficiary_data": None,
            "reversal_data": None,

            # Evidence & Reconciliation Intelligence Layer
            "evidence_items": [],
            "normalized_evidence": [],
            "reconciliation_case": "UNKNOWN",
            "reconciliation_report": None,
            "evidence_summary": None,
            "conflicts_detected": [],
            "missing_evidence": [],
            "fact_certainty_score": 1.0,
            "root_cause_hypothesis": None,

            # Policy Retrieval & RAG Service
            "policy_record": None,
            "retrieved_policies": [],
            "tat_status": "UNKNOWN",
            "action_eligibility": None,

            # Decision & Resolution Reasoning Engine
            "resolution_assessment": None,
            "decision": None,
            "action_type": None,
            "decision_reason_code": None,
            "decision_reason": None,


            # Gate & Action
            "action_proposal": None,
            "policy_gate_passed": False,
            "policy_gate_rejection_reason": None,
            "action_result": None,

            # Verification
            "verification_result": None,
            "verification_passed": False,

            # Escalation & Communication
            "escalation_reason": None,
            "escalation_packet": None,
            "notifications": [],
            "resolution_summary": None,

            # Lifecycle
            "current_status": "NEW",
            "steps_completed": 0,
            "current_node": "intake",
            "max_steps_limit": 15,

            # Trace
            "tool_calls": [],
            "audit_trail": [],
            "errors": []
        }

        try:
            graph = build_tat_agent_graph(self.db)
            final_state = graph.invoke(initial_state)

            # Persist execution status
            agent_run.status = "SUCCESS" if not final_state.get("errors") else "FAILED"
            agent_run.steps_completed = final_state.get("steps_completed", 0)
            agent_run.completed_at = datetime.now(timezone.utc)
            if final_state.get("errors"):
                agent_run.error_message = "; ".join(final_state.get("errors", []))

            # Persist individual tool calls
            for tc in final_state.get("tool_calls", []):
                tool_call_obj = ToolCall(
                    id=str(uuid.uuid4()),
                    agent_run_id=run_id,
                    tool_name=tc["tool_name"],
                    input_payload=tc["input_payload"],
                    output_payload=tc["output_payload"],
                    status=tc["status"]
                )
                self.db.add(tool_call_obj)

            # Persist Case status updates
            final_status_str = final_state.get("current_status")
            if final_status_str in CaseStatus.__members__:
                case.status = CaseStatus[final_status_str]
            case.resolution_summary = final_state.get("resolution_summary") or case.resolution_summary
            
            self.db.commit()
            logger.info(f"Agent run {run_id} completed for case {case.case_number} with status {case.status}")
            return agent_run

        except Exception as e:
            self.db.rollback()
            agent_run.status = "FAILED"
            agent_run.error_message = str(e)
            agent_run.completed_at = datetime.now(timezone.utc)
            case.status = CaseStatus.FAILED
            self.db.commit()
            logger.error(f"Agent run {run_id} failed: {e}", exc_info=True)
            raise e
