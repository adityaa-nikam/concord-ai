from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
import logging

from app.schemas.evidence import NormalizedEvidenceSet, EvidenceReliability, EvidenceFreshness

logger = logging.getLogger("tat_guardian.schemas.reconciliation")


class Conflict(BaseModel):
    conflict_detected: bool = True
    conflict_type: str        # CROSS_SYSTEM_STATE_CONFLICT, POST_ACTION_VERIFICATION_CONFLICT, etc.
    severity: str             # CRITICAL, HIGH, MEDIUM, LOW
    sources: List[str]        # ["gateway", "ledger", "beneficiary"]
    summary: str


class EvidenceFact(BaseModel):
    source: str
    fact: str
    value: Any
    is_system_of_record: bool


class ReconciliationResult(BaseModel):
    status: Literal["CONSISTENT", "CONFLICT", "INCOMPLETE", "ALREADY_RESOLVED"]
    reconciled_case_category: str # CROSS_SYSTEM_CONFLICT, CONSISTENT_SUCCESS, ALREADY_RESOLVED, PENDING_CONSISTENT, BENEFICIARY_STATE_UNKNOWN
    conflicts: List[Conflict]
    known_facts: List[EvidenceFact]
    missing_information: List[str]
    unresolved_questions: List[str]
    recommended_next_evidence: List[str]
    summary: str


class DeterministicReconciliationEngine:
    """Signature capability of Concord-AI: Analyzes normalized evidence sets deterministically."""

    @classmethod
    def reconcile_evidence_set(cls, ev_set: NormalizedEvidenceSet) -> ReconciliationResult:
        known_facts: List[EvidenceFact] = []
        conflicts: List[Conflict] = []
        missing_info: List[str] = list(ev_set.missing_fields)
        unresolved_questions: List[str] = []
        recommended_next: List[str] = []

        # Extract normalized status maps
        field_map = {(i.source, i.field): i.value for i in ev_set.items}
        
        gw_stat = field_map.get(("gateway", "gateway_status"), "MISSING")
        npci_stat = field_map.get(("gateway", "npci_status"), "MISSING")
        debit_stat = field_map.get(("ledger", "debit_status"), "MISSING")
        credit_stat = field_map.get(("beneficiary", "credit_status"), "UNKNOWN")
        rev_stat = field_map.get(("reversal", "reversal_status"), "NOT_INITIATED")

        # Build known facts list
        for i in ev_set.items:
            known_facts.append(EvidenceFact(
                source=i.source,
                fact=f"{i.source}.{i.field}",
                value=i.value,
                is_system_of_record=(i.reliability == EvidenceReliability.SYSTEM_OF_RECORD)
            ))

        # Check explicit conflict scenarios in deterministic order

        # 1. Reversal already completed
        if rev_stat == "COMPLETED" or debit_stat == "REVERSED":
            if rev_stat == "COMPLETED" and debit_stat == "PENDING":
                # Conflict E: Reversal COMPLETED vs Ledger PENDING
                conflicts.append(Conflict(
                    conflict_type="POST_ACTION_VERIFICATION_CONFLICT",
                    severity="HIGH",
                    sources=["reversal", "ledger"],
                    summary="Reversal Engine reports COMPLETED, but Core Banking Ledger debit status remains PENDING."
                ))
            else:
                # Conflict B: Reversal completed without contradiction
                pass

            reconciled_category = "ALREADY_RESOLVED"
            status = "ALREADY_RESOLVED" if not conflicts else "CONFLICT"
            summary = "Reversal has already been processed prior. System is in resolved state."

        # 2. Beneficiary confirmed credited
        elif credit_stat == "CREDITED":
            reconciled_category = "CONSISTENT_SUCCESS"
            status = "CONSISTENT"
            summary = "Beneficiary bank confirms credit completed successfully."

        # 3. Administrative bank hold
        elif debit_stat == "ON_HOLD":
            conflicts.append(Conflict(
                conflict_type="INCONSISTENT_BANK_HOLD",
                severity="CRITICAL",
                sources=["ledger"],
                summary="Core Banking System has placed an administrative hold on the account debit."
            ))
            reconciled_category = "CROSS_SYSTEM_CONFLICT"
            status = "CONFLICT"
            unresolved_questions.append("Why was an administrative hold placed on the remitter account?")
            recommended_next.append("Escalate to Tier 2 Human Ops for CBS Hold Review")
            summary = "Remitter bank placed an administrative hold on the transaction."

        # 4. Conflict A / C: Gateway SUCCESS but Ledger PENDING or Beneficiary NOT_CREDITED
        elif gw_stat == "SUCCESS" and (debit_stat == "PENDING" or credit_stat == "NOT_CREDITED"):
            conflicts.append(Conflict(
                conflict_type="CROSS_SYSTEM_STATE_CONFLICT",
                severity="HIGH",
                sources=["gateway", "ledger", "beneficiary"],
                summary=f"Payment Gateway reports SUCCESS while Ledger is '{debit_stat}' and Beneficiary credit is '{credit_stat}'."
            ))
            reconciled_category = "CROSS_SYSTEM_CONFLICT"
            status = "CONFLICT"
            unresolved_questions.append("Did NPCI switch clearing time out before reaching beneficiary bank?")
            recommended_next.append("Retrieve applicable NPCI T+1 Auto-Reversal policy guidelines")
            summary = "Cross-system conflict detected: Gateway reports success while beneficiary is uncredited."

        # 5. Debited but Beneficiary Not Credited
        elif debit_stat == "DEBITED" and credit_stat == "NOT_CREDITED":
            conflicts.append(Conflict(
                conflict_type="DEBITED_BENEFICIARY_UNCREDITED",
                severity="HIGH",
                sources=["ledger", "beneficiary"],
                summary="Remitter account is debited ₹, but Beneficiary bank confirms funds were NOT credited."
            ))
            reconciled_category = "CROSS_SYSTEM_CONFLICT"
            status = "CONFLICT"
            recommended_next.append("Retrieve NPCI T+1 Auto-Reversal Policy")
            summary = "Customer debited but payee uncredited due to NPCI switch timeout."

        # 6. Conflict D: Gateway PENDING, Ledger PENDING
        elif (gw_stat == "PENDING" or gw_stat == "MISSING") and (debit_stat == "PENDING" or debit_stat == "MISSING"):
            reconciled_category = "PENDING_CONSISTENT"
            status = "CONSISTENT"
            summary = "Transaction pending consistently within clearing buffer."
            if credit_stat == "UNKNOWN" or credit_stat == "MISSING":
                missing_info.append("beneficiary_credit_status")
                unresolved_questions.append("What is the final credit status at the beneficiary bank?")
                recommended_next.append("get_beneficiary_status()")

        # 7. Beneficiary State Unknown
        elif credit_stat == "UNKNOWN" or credit_stat == "MISSING":
            reconciled_category = "BENEFICIARY_STATE_UNKNOWN"
            status = "INCOMPLETE"
            missing_info.append("beneficiary_credit_status")
            unresolved_questions.append("Beneficiary Bank switch did not return credit status.")
            recommended_next.append("get_beneficiary_status()")
            summary = "Beneficiary bank credit status is unconfirmed."

        else:
            reconciled_category = "CROSS_SYSTEM_CONFLICT"
            status = "CONFLICT"
            summary = "Operational state discrepancy detected across system boundaries."

        # Detect stale data conflicts
        if ev_set.has_stale_data:
            conflicts.append(Conflict(
                conflict_type="STALE_TELEMETRY_WARNING",
                severity="MEDIUM",
                sources=["gateway", "ledger"],
                summary="One or more telemetry items contain stale timestamps older than active threshold."
            ))
            recommended_next.append("Refresh multi-system telemetry status")

        logger.info(f"Deterministic reconciliation completed: status={status}, category={reconciled_category}, conflicts={len(conflicts)}")

        return ReconciliationResult(
            status=status,
            reconciled_case_category=reconciled_category,
            conflicts=conflicts,
            known_facts=known_facts,
            missing_information=missing_info,
            unresolved_questions=unresolved_questions,
            recommended_next_evidence=recommended_next,
            summary=summary
        )
