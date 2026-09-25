from typing import Dict, Any, Optional
import logging

from app.schemas.reconciliation import ReconciliationResult
from app.services.decision_service import DecisionSupportResult

logger = logging.getLogger("tat_guardian.services.summary")


class CaseSummaryService:
    """Generates concise, operational, auditable case summaries without chain-of-thought exposure."""

    @classmethod
    def generate_case_summary(
        cls,
        case_number: str,
        issue_description: str,
        amount: float,
        reconciliation: ReconciliationResult,
        decision_res: DecisionSupportResult,
        verification_passed: bool = False,
        is_resolved: bool = False
    ) -> str:
        
        problem_str = f"Customer reported a dispute (Case {case_number}) for ₹{amount:,.2f}: \"{issue_description}\"."
        
        # Facts summary
        facts_lines = []
        for fact in reconciliation.known_facts[:4]:
            facts_lines.append(f"{fact.fact}: {fact.value}")
        facts_str = "Known system telemetry: " + "; ".join(facts_lines) + "."

        conflict_str = f"Reconciliation state: {reconciliation.reconciled_case_category}. {reconciliation.summary}"

        policy_str = f"Applicable policy: {decision_res.policy_id}."

        decision_str = f"Concord-AI decision: {decision_res.decision} (Action: {decision_res.action or 'NONE'}, Reason: {decision_res.reason_code})."

        if is_resolved and verification_passed:
            outcome_str = "Post-action multi-source verification PASSED. Dispute resolved autonomously."
        elif decision_res.decision == "ESCALATE":
            outcome_str = f"Case escalated to Tier 2 Human Ops queue. Reason: {decision_res.escalation_reason or 'State ambiguity'}."
        elif decision_res.decision == "WAIT":
            outcome_str = "Case placed in monitoring state awaiting NPCI clearing buffer."
        else:
            outcome_str = f"Case status updated to {decision_res.decision}."

        summary = "\n\n".join([problem_str, facts_str, conflict_str, policy_str, decision_str, outcome_str])
        return summary
