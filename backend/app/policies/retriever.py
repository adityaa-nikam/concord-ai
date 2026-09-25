from typing import List, Dict, Any, Optional
import logging
from app.policies.schemas import PolicyRecordSchema, PolicyCitation
from app.policies.loader import PolicyDocumentLoader

logger = logging.getLogger("tat_guardian.policies.retriever")


class PolicyRAGRetriever:
    """Clean, metadata-filtered RAG Policy Retriever providing citations and traceability."""

    def __init__(self):
        self._policies: List[PolicyRecordSchema] = PolicyDocumentLoader.load_all_policies()

    def retrieve_policies(
        self,
        transaction_type: str,
        reconciled_case_category: str,
        amount: float = 0.0,
        debit_status: str = "UNKNOWN",
        credit_status: str = "UNKNOWN",
        is_reversed: bool = False,
        missing_evidence: Optional[List[str]] = None
    ) -> List[PolicyCitation]:
        citations: List[PolicyCitation] = []
        missing = missing_evidence or []

        for p in self._policies:
            relevance = 0.0
            used_for = []

            # 1. Idempotency Guard check
            if p.policy_id == "POL-PAYTM-IDEMPOTENT-RETRY" and (is_reversed or reconciled_case_category == "ALREADY_RESOLVED"):
                relevance = 1.0
                used_for = ["idempotency_check", "action_prohibition"]

            # 2. High Value Risk check
            elif p.policy_id == "POL-PAYTM-HIGH-VALUE-ESCALATION" and (amount > 50000.0 or debit_status == "ON_HOLD"):
                relevance = 0.99
                used_for = ["risk_threshold_check", "human_escalation_authorization"]

            # 3. Pending Clearing Buffer check
            elif p.policy_id == "POL-PAYTM-CLEARING-BUFFER" and reconciled_case_category == "PENDING_CONSISTENT":
                relevance = 0.95
                used_for = ["clearing_window_check", "monitoring_state_setting"]

            # 4. RBI Regulatory Rule for UPI Transfer
            elif p.policy_id == "POL-RBI-UPI-TRANSFER-T1" and transaction_type == "UPI_TRANSFER" and (reconciled_case_category == "CROSS_SYSTEM_CONFLICT" or debit_status == "DEBITED"):
                relevance = 0.98
                used_for = ["TAT_evaluation", "auto_reversal_eligibility", "compensation_calculation"]

            # 5. RBI Regulatory Rule for UPI Merchant Payment
            elif p.policy_id == "POL-RBI-UPI-MERCHANT-T5" and transaction_type == "UPI_MERCHANT_PAYMENT" and (reconciled_case_category == "CROSS_SYSTEM_CONFLICT" or debit_status == "DEBITED"):
                relevance = 0.98
                used_for = ["merchant_TAT_evaluation", "settlement_window_check"]

            if relevance > 0.0:
                citations.append(PolicyCitation(
                    policy_id=p.policy_id,
                    source=p.source,
                    source_type=p.source_type,
                    section=p.tat_rule,
                    retrieval_relevance=relevance,
                    content_excerpt=p.summary,
                    used_for=used_for
                ))

        # Sort by relevance descending
        citations.sort(key=lambda x: x.retrieval_relevance, reverse=True)

        if not citations:
            # Fallback policy citation
            citations.append(PolicyCitation(
                policy_id="POL-FALLBACK-MANUAL-REVIEW",
                source="Paytm Internal Fallback Standard",
                source_type="PROTOTYPE_OPERATIONAL",
                section="MANUAL_REVIEW",
                retrieval_relevance=0.5,
                content_excerpt="Default dispute handling guidelines for unclassified state.",
                used_for=["manual_review_fallback"]
            ))

        logger.info(f"Retrieved {len(citations)} policy citations. Top citation: {citations[0].policy_id}")
        return citations

    def get_policy_by_id(self, policy_id: str) -> Optional[PolicyRecordSchema]:
        for p in self._policies:
            if p.policy_id == policy_id:
                return p
        return None
