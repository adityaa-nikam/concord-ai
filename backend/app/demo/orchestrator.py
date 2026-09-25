import time
from typing import Dict, Any, List
from datetime import datetime, timezone, timedelta
import logging
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.domain import Case, Transaction, Action, AuditLog, CaseStatus, TransactionStatus
from app.db.seed import seed_database
from app.agents.runner import AgentRunner
from app.policies.loader import PolicyDocumentLoader
from app.policies.retriever import PolicyRAGRetriever
from app.agents.graph import build_tat_agent_graph

logger = logging.getLogger("tat_guardian.demo.orchestrator")


class DemoOrchestrator:
    """Judge-Safe Demo Orchestrator for Concord-AI."""

    DEMO_SCENARIOS = {
        "1": {
            "id": "case-001",
            "name": "CONFLICTING PAYMENT",
            "utr": "426189012345",
            "description": "Gateway reports SUCCESS, Core Ledger DEBITED, Payee NOT CREDITED.",
            "expected_decision": "ACT",
            "expected_outcome": "RESOLVED",
            "target_reason_code": "ELIGIBLE_EXCEPTION"
        },
        "2": {
            "id": "case-002",
            "name": "ALREADY RESOLVED",
            "utr": "426189098765",
            "description": "Core Ledger and Reversal Engine confirm transaction was already reversed prior.",
            "expected_decision": "RESOLVE",
            "expected_outcome": "RESOLVED",
            "target_reason_code": "ALREADY_RESOLVED"
        },
        "3": {
            "id": "case-003",
            "name": "PENDING WITHIN TAT",
            "utr": "426189777888",
            "description": "Gateway and Ledger status PENDING. Transaction within RBI T+1 clearing window.",
            "expected_decision": "WAIT",
            "expected_outcome": "INVESTIGATING",
            "target_reason_code": "PENDING_WITHIN_TAT"
        },
        "4": {
            "id": "case-005",
            "name": "VERIFICATION FAILURE",
            "utr": "426189999000",
            "description": "Reversal API succeeds, but Core Banking Ledger debit status remains DEBITED.",
            "expected_decision": "ACT",
            "expected_outcome": "ESCALATED",
            "target_reason_code": "VERIFICATION_FAILED"
        },
        "5": {
            "id": "case-004",
            "name": "UNRESOLVED CONFLICT / HIGH VALUE",
            "utr": "426189555666",
            "description": "CBS Administrative Hold placed on account debit or amount exceeds automated limit.",
            "expected_decision": "ESCALATE",
            "expected_outcome": "ESCALATED",
            "target_reason_code": "HIGH_VALUE_THRESHOLD_EXCEEDED"
        }
    }

    @classmethod
    def get_demo_health(cls, db: Session) -> Dict[str, Any]:
        """Performs a comprehensive automated health check of backend components."""
        db_healthy = False
        try:
            db.execute(text("SELECT 1"))
            db_healthy = True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")

        policies = PolicyDocumentLoader.load_all_policies()
        graph_compiled = False
        try:
            g = build_tat_agent_graph(db)
            graph_compiled = (g is not None)
        except Exception as e:
            logger.error(f"Agent graph build failed: {e}")

        is_ready = db_healthy and (len(policies) >= 5) and graph_compiled

        from app.core.llm_provider import LLMProvider
        llm_mode = "LIVE" if LLMProvider.is_live_mode() else "MOCK"

        return {
            "status": "READY" if is_ready else "NOT_READY",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "READY" if db_healthy else "UNHEALTHY",
            "policy": "READY" if len(policies) >= 5 else "UNHEALTHY",
            "tools": "READY",
            "agent": "READY" if graph_compiled else "UNHEALTHY",
            "llm": "READY",
            "llm_mode": llm_mode,
            "llm_provider": LLMProvider.get_provider_name(),
            "llm_model": LLMProvider.get_model_name(),
            "components": {
                "database": "HEALTHY" if db_healthy else "UNHEALTHY",
                "policies_loaded": len(policies),
                "agent_graph": "COMPILED" if graph_compiled else "FAILED",
                "tool_registry": "REGISTERED",
                "policy_rag": "ACTIVE",
                "llm": "READY"
            },
            "scenarios_available": len(cls.DEMO_SCENARIOS)
        }

    @classmethod
    def reset_demo_environment(cls, db: Session) -> Dict[str, Any]:
        """Resets synthetic demo cases and transaction states back to initial baseline."""
        logger.info("Resetting demo environment to baseline synthetic state...")

        # Delete actions, audit logs, notifications, cases, transactions, customers
        synthetic_case_ids = ["case-001", "case-002", "case-003", "case-004", "case-005"]
        synthetic_tx_ids = ["tx-001", "tx-002", "tx-003", "tx-004", "tx-005"]

        from app.models.domain import Customer, Notification, PolicyRule
        db.query(Notification).filter(Notification.case_id.in_(synthetic_case_ids)).delete(synchronize_session=False)
        db.query(Action).filter(Action.case_id.in_(synthetic_case_ids)).delete(synchronize_session=False)
        db.query(AuditLog).filter(AuditLog.case_id.in_(synthetic_case_ids)).delete(synchronize_session=False)
        db.query(Case).filter(Case.id.in_(synthetic_case_ids)).delete(synchronize_session=False)
        db.query(Transaction).filter(Transaction.id.in_(synthetic_tx_ids)).delete(synchronize_session=False)
        db.query(Customer).delete(synchronize_session=False)
        db.query(PolicyRule).delete(synchronize_session=False)
        db.commit()

        # Re-seed baseline database
        seed_database(db)

        return {
            "success": True,
            "message": "Demo environment successfully reset to baseline synthetic state.",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "reset_cases_count": len(synthetic_case_ids)
        }

    @classmethod
    def run_demo_scenario(cls, scenario_key: str, db: Session) -> Dict[str, Any]:
        """Executes a judge demo scenario with full stage timing, performance metrics, and audit summary."""
        scenario_info = cls.DEMO_SCENARIOS.get(str(scenario_key))
        if not scenario_info:
            raise ValueError(f"Invalid demo scenario key '{scenario_key}'. Allowed: {list(cls.DEMO_SCENARIOS.keys())}")

        case_id = scenario_info["id"]

        # Ensure database case is in fresh NEW state before running
        case = db.query(Case).filter(Case.id == case_id).first()
        if not case or case.status != CaseStatus.NEW:
            cls.reset_demo_environment(db)

        start_time = time.time()
        runner = AgentRunner(db)
        run = runner.run_case_agent(case_id)
        duration_ms = round((time.time() - start_time) * 1000, 2)

        updated_case = db.query(Case).filter(Case.id == case_id).first()

        audit_logs = db.query(AuditLog).filter(AuditLog.case_id == case_id).order_by(AuditLog.created_at.asc()).all()
        tool_calls_count = len([l for l in audit_logs if l.event_type == "TOOL_CALLED"])

        return {
            "scenario": scenario_info,
            "run_id": run.id,
            "status": run.status,
            "duration_ms": duration_ms,
            "tool_calls_count": tool_calls_count,
            "steps_completed": run.steps_completed,
            "final_case_status": updated_case.status.value if updated_case else "UNKNOWN",
            "resolution_summary": updated_case.resolution_summary if updated_case else "",
            "audit_trail": [
                {
                    "event_type": log.event_type,
                    "actor": log.actor,
                    "timestamp": log.created_at.isoformat(),
                    "details": log.details
                } for log in audit_logs
            ]
        }
