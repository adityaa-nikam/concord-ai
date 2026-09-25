from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger("tat_guardian.services.policy_rag")


class PolicyMatch(BaseModel):
    policy_id: str
    title: str
    clause_reference: str
    summary: str
    rule_condition: str
    permitted_actions: List[str]
    prohibited_actions: List[str]
    auto_execution_allowed: bool
    min_confidence_required: float
    max_amount_limit: Optional[float] = None
    relevance_score: float = 1.0


class PolicyKnowledgeBase:
    """NPCI & Paytm Internal Policy Knowledge Base."""

    RULES: List[Dict[str, Any]] = [
        {
            "policy_id": "POL-NPCI-T1-AUTOREVERSAL",
            "title": "NPCI T+1 Auto-Reversal Rule for Failed UPI Transfers",
            "clause_reference": "NPCI/UPI/OC-84/2021 Clause 4.2",
            "summary": "Where customer account is debited but beneficiary bank credit status is uncredited, transaction is eligible for T+1 auto-reversal.",
            "rule_condition": "CROSS_SYSTEM_CONFLICT (DEBITED & UNCREDITED)",
            "permitted_actions": ["INITIATE_REVERSAL", "SEND_NOTIFICATION"],
            "prohibited_actions": [],
            "auto_execution_allowed": True,
            "min_confidence_required": 0.85,
            "max_amount_limit": 50000.0
        },
        {
            "policy_id": "POL-NPCI-CLEARING-BUFFER",
            "title": "NPCI 15-Minute Clearing Window Buffer",
            "clause_reference": "NPCI/UPI/OC-99/2022 Clause 2.1",
            "summary": "Pending transactions initiated within 15 minutes of intake must remain in monitoring state to allow NPCI clearing reconciliation.",
            "rule_condition": "PENDING_CONSISTENT (Window < 15 mins)",
            "permitted_actions": ["WAIT_AND_POLL"],
            "prohibited_actions": ["INITIATE_REVERSAL"],
            "auto_execution_allowed": True,
            "min_confidence_required": 0.90,
            "max_amount_limit": None
        },
        {
            "policy_id": "POL-PAYTM-IDEMPOTENT-RETRY",
            "title": "Paytm Idempotent Financial Reversal Guard",
            "clause_reference": "PAYTM/FINOPS/SEC-101",
            "summary": "If transaction is already marked REVERSED in Core Banking or Reversal Engine, duplicate reversal calls are strictly prohibited.",
            "rule_condition": "ALREADY_RESOLVED (Reversed == True)",
            "permitted_actions": ["SEND_NOTIFICATION", "CLOSE_CASE"],
            "prohibited_actions": ["INITIATE_REVERSAL"],
            "auto_execution_allowed": True,
            "min_confidence_required": 0.95,
            "max_amount_limit": None
        },
        {
            "policy_id": "POL-NPCI-HIGH-VALUE-RISK",
            "title": "High-Value Dispute Human Escalation Rule",
            "clause_reference": "NPCI/UPI/RISK-302 Clause 7.1",
            "summary": "Disputed UPI transactions exceeding ₹50,000 with cross-system ambiguity require manual authorization from Tier 2 Human Ops.",
            "rule_condition": "Amount > ₹50,000 OR State Ambiguous",
            "permitted_actions": ["CREATE_ESCALATION"],
            "prohibited_actions": ["INITIATE_REVERSAL"],
            "auto_execution_allowed": False,
            "min_confidence_required": 0.99,
            "max_amount_limit": 50000.0
        },
        {
            "policy_id": "POL-BANK-HOLD-ESCALATION",
            "title": "Core Banking System Hold Escalation Rule",
            "clause_reference": "PAYTM/CBS/HOLD-404",
            "summary": "Where remitter ledger is ON_HOLD or Beneficiary state is UNKNOWN, automated action is prohibited and requires Human Ops review.",
            "rule_condition": "CBS ON_HOLD OR BENEFICIARY_STATE_UNKNOWN",
            "permitted_actions": ["CREATE_ESCALATION"],
            "prohibited_actions": ["INITIATE_REVERSAL"],
            "auto_execution_allowed": False,
            "min_confidence_required": 0.95,
            "max_amount_limit": None
        }
    ]


class PolicyRAGService:
    """Lightweight, fact-preserving Policy Retrieval & RAG Service."""

    @classmethod
    def retrieve_applicable_policies(
        cls,
        issue_type: str,
        reconciled_case: str,
        amount: Optional[float] = 0.0,
        debit_status: Optional[str] = None,
        credit_status: Optional[str] = None,
        is_reversed: bool = False,
        missing_evidence: Optional[List[str]] = None
    ) -> List[PolicyMatch]:
        """Retrieves matching policy rules based on reconciled system facts."""

        matches: List[PolicyMatch] = []
        amount_val = amount or 0.0
        missing = missing_evidence or []

        for rule in PolicyKnowledgeBase.RULES:
            policy_id = rule["policy_id"]
            relevance = 0.0

            if policy_id == "POL-PAYTM-IDEMPOTENT-RETRY" and (is_reversed or reconciled_case == "ALREADY_RESOLVED"):
                relevance = 1.0
            elif policy_id == "POL-BANK-HOLD-ESCALATION" and (debit_status == "ON_HOLD" or credit_status == "UNKNOWN" or missing or reconciled_case == "BENEFICIARY_STATE_UNKNOWN"):
                relevance = 1.0
            elif policy_id == "POL-NPCI-HIGH-VALUE-RISK" and amount_val > 50000.0:
                relevance = 1.0
            elif policy_id == "POL-NPCI-CLEARING-BUFFER" and (reconciled_case == "PENDING_CONSISTENT" or issue_type == "PENDING_TRANSACTION_STATUS"):
                relevance = 0.95
            elif policy_id == "POL-NPCI-T1-AUTOREVERSAL" and reconciled_case == "CROSS_SYSTEM_CONFLICT" and debit_status == "DEBITED":
                relevance = 0.98

            if relevance > 0.0:
                matches.append(PolicyMatch(
                    policy_id=rule["policy_id"],
                    title=rule["title"],
                    clause_reference=rule["clause_reference"],
                    summary=rule["summary"],
                    rule_condition=rule["rule_condition"],
                    permitted_actions=rule["permitted_actions"],
                    prohibited_actions=rule["prohibited_actions"],
                    auto_execution_allowed=rule["auto_execution_allowed"],
                    min_confidence_required=rule["min_confidence_required"],
                    max_amount_limit=rule["max_amount_limit"],
                    relevance_score=relevance
                ))

        # Sort matches by relevance score descending
        matches.sort(key=lambda x: x.relevance_score, reverse=True)

        if not matches:
            # Fallback default review rule
            matches.append(PolicyMatch(
                policy_id="POL-GENERIC-MANUAL-REVIEW",
                title="Generic Dispute Review Guidelines",
                clause_reference="PAYTM/DISPUTE/GEN-001",
                summary="Standard manual dispute review required for unclassified exception states.",
                rule_condition="Unclassified State",
                permitted_actions=["CREATE_ESCALATION"],
                prohibited_actions=["INITIATE_REVERSAL"],
                auto_execution_allowed=False,
                min_confidence_required=0.95,
                relevance_score=0.5
            ))

        logger.info(f"Retrieved {len(matches)} matching policy rules. Top match: {matches[0].policy_id}")
        return matches

    @classmethod
    def validate_policy_against_facts(cls, policy_match: PolicyMatch, facts: Dict[str, Any]) -> Dict[str, Any]:
        """Safeguard: Ensures policy documents NEVER override physical system facts!"""
        is_reversed = facts.get("is_reversed", False)
        if is_reversed and "INITIATE_REVERSAL" in policy_match.permitted_actions:
            return {
                "valid": False,
                "reason": "FACT CONSTRAINED: System fact confirms transaction is already REVERSED. Policy cannot grant duplicate reversal."
            }
        
        amount = facts.get("amount", 0.0)
        if policy_match.max_amount_limit and amount > policy_match.max_amount_limit and policy_match.auto_execution_allowed:
            return {
                "valid": False,
                "reason": f"AMOUNT OVERRIDE: Amount ₹{amount} exceeds policy limit ₹{policy_match.max_amount_limit} for automated action."
            }

        return {"valid": True, "reason": "Policy matches system facts."}
