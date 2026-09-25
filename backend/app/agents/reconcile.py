from datetime import datetime, timezone
from typing import Dict, Any, List
import logging
from app.agents.state import EvidenceItem, ConflictRecord

logger = logging.getLogger("tat_guardian.agents.reconcile")


class PaymentEvidenceReconciler:
    """Core Autonomous Reconciliation Engine for analyzing multi-system payment evidence streams."""

    @classmethod
    def reconcile(
        cls,
        tx_data: Dict[str, Any],
        gw_data: Dict[str, Any],
        ledger_data: Dict[str, Any],
        bene_data: Dict[str, Any],
        rev_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Reconciles evidence across 5 sources and classifies into explicit case categories."""

        now_iso = datetime.now(timezone.utc).isoformat()
        evidence_items: List[EvidenceItem] = []
        conflicts: List[ConflictRecord] = []
        missing_evidence: List[str] = []

        # 1. Build Explicit Evidence Items
        if tx_data:
            evidence_items.append({"source": "transaction", "field": "amount", "value": tx_data.get("amount"), "timestamp": now_iso})
            evidence_items.append({"source": "transaction", "field": "status", "value": tx_data.get("status"), "timestamp": now_iso})
        else:
            missing_evidence.append("TRANSACTION_SERVICE")

        if gw_data and gw_data.get("found"):
            evidence_items.append({"source": "gateway", "field": "gateway_status", "value": gw_data.get("gateway_status"), "timestamp": now_iso})
            evidence_items.append({"source": "gateway", "field": "npci_status", "value": gw_data.get("npci_status"), "timestamp": now_iso})
        else:
            missing_evidence.append("PAYMENT_GATEWAY")

        if ledger_data and ledger_data.get("found"):
            evidence_items.append({"source": "ledger", "field": "debit_status", "value": ledger_data.get("debit_status"), "timestamp": now_iso})
        else:
            missing_evidence.append("CORE_BANKING_LEDGER")

        if bene_data and bene_data.get("found"):
            evidence_items.append({"source": "beneficiary", "field": "credit_status", "value": bene_data.get("credit_status"), "timestamp": now_iso})
        else:
            missing_evidence.append("BENEFICIARY_BANK")

        if rev_data and rev_data.get("found"):
            evidence_items.append({"source": "reversal", "field": "is_reversed", "value": rev_data.get("is_reversed"), "timestamp": now_iso})

        # Extract status strings
        gw_status = (gw_data.get("gateway_status") or "UNKNOWN").upper() if gw_data else "UNKNOWN"
        npci_status = (gw_data.get("npci_status") or "UNKNOWN").upper() if gw_data else "UNKNOWN"
        debit_status = (ledger_data.get("debit_status") or "UNKNOWN").upper() if ledger_data else "UNKNOWN"
        credit_status = (bene_data.get("credit_status") or "UNKNOWN").upper() if bene_data else "UNKNOWN"
        is_reversed = (rev_data.get("is_reversed", False)) or (tx_data.get("status") == "REVERSED") or (debit_status == "REVERSED") if tx_data else False

        # 2. Classify explicit reconciliation case categories in strict logical order
        if is_reversed or debit_status == "REVERSED":
            reconciled_case = "ALREADY_RESOLVED"
            conflicts.append({
                "conflict_type": "REVERSAL_ALREADY_COMPLETED",
                "description": "Reversal has already been executed prior. No duplicate action allowed.",
                "severity": "LOW",
                "system_a": "ReversalEngine",
                "system_b": "BankLedger",
                "state_a": "REVERSED",
                "state_b": debit_status
            })
        elif credit_status == "CREDITED":
            reconciled_case = "CONSISTENT_SUCCESS"
        elif gw_status == "PENDING" and debit_status in ["DEBITED", "ON_HOLD"]:
            reconciled_case = "CROSS_SYSTEM_CONFLICT"
            conflict_type = "INCONSISTENT_BANK_HOLD" if debit_status == "ON_HOLD" else "GATEWAY_LEDGER_MISMATCH"
            conflicts.append({
                "conflict_type": conflict_type,
                "description": f"Gateway reports '{gw_status}' but Ledger reports '{debit_status}'.",
                "severity": "CRITICAL" if debit_status == "ON_HOLD" else "HIGH",
                "system_a": "PaymentGateway",
                "system_b": "BankLedger",
                "state_a": gw_status,
                "state_b": debit_status
            })
        elif gw_status == "PENDING" and debit_status == "PENDING":
            reconciled_case = "PENDING_CONSISTENT"
        elif credit_status == "UNKNOWN":
            reconciled_case = "BENEFICIARY_STATE_UNKNOWN"
            conflicts.append({
                "conflict_type": "BENEFICIARY_STATE_UNCONFIRMED",
                "description": "Beneficiary Bank status is UNKNOWN. System must not guess.",
                "severity": "HIGH",
                "system_a": "BeneficiaryBank",
                "system_b": "PaymentGateway",
                "state_a": credit_status,
                "state_b": gw_status
            })
        elif debit_status == "DEBITED" and credit_status == "NOT_CREDITED":
            reconciled_case = "CROSS_SYSTEM_CONFLICT"
            conflicts.append({
                "conflict_type": "DEBITED_BENEFICIARY_UNCREDITED",
                "description": f"Customer debited ₹{tx_data.get('amount', 0)}, but Beneficiary confirms funds NOT credited.",
                "severity": "HIGH",
                "system_a": "BankLedger",
                "system_b": "BeneficiaryBank",
                "state_a": debit_status,
                "state_b": credit_status
            })
        else:
            reconciled_case = "CROSS_SYSTEM_CONFLICT"

        # Calculate fact certainty score (1.0 = full certainty, reduced by missing telemetry or ambiguity)
        base_certainty = 1.0
        if missing_evidence:
            base_certainty -= 0.15 * len(missing_evidence)
        if credit_status == "UNKNOWN":
            base_certainty -= 0.20
        if debit_status == "ON_HOLD":
            base_certainty -= 0.15
        fact_certainty_score = max(0.5, round(base_certainty, 2))

        # Build root cause hypothesis
        if reconciled_case == "ALREADY_RESOLVED":
            root_cause_hypothesis = "Transaction was already reversed prior. System is in consistent reversed state."
        elif reconciled_case == "CONSISTENT_SUCCESS":
            root_cause_hypothesis = "Transaction cleared successfully across remitter and beneficiary banks."
        elif reconciled_case == "PENDING_CONSISTENT":
            root_cause_hypothesis = "Transaction is currently pending clearing within the standard NPCI settlement buffer."
        elif debit_status == "ON_HOLD":
            root_cause_hypothesis = "Remitter Core Banking System placed an administrative hold on the account/debit."
        elif credit_status == "UNKNOWN":
            root_cause_hypothesis = "Beneficiary bank switch failed to respond to credit confirmation query."
        elif debit_status == "DEBITED" and credit_status == "NOT_CREDITED":
            root_cause_hypothesis = f"NPCI switch timeout ({npci_status}) after remitter debit resulted in uncredited beneficiary state."
        else:
            root_cause_hypothesis = "Operational discrepancy detected between payment gateway and core banking ledger."

        summary = {
            "utr": tx_data.get("utr") if tx_data else None,
            "amount": tx_data.get("amount") if tx_data else None,
            "debit_status": debit_status,
            "credit_status": credit_status,
            "gateway_status": gw_status,
            "npci_status": npci_status,
            "is_reversed": is_reversed,
            "reconciled_case": reconciled_case,
            "has_conflicts": len(conflicts) > 0,
            "primary_conflict": conflicts[0]["conflict_type"] if conflicts else "NONE",
            "fact_certainty_score": fact_certainty_score,
            "root_cause_hypothesis": root_cause_hypothesis
        }

        logger.info(f"Evidence reconciliation output: case category={reconciled_case}, certainty={fact_certainty_score}, conflicts={len(conflicts)}")

        return {
            "evidence_items": evidence_items,
            "reconciliation_case": reconciled_case,
            "evidence_summary": summary,
            "conflicts_detected": conflicts,
            "missing_evidence": missing_evidence,
            "fact_certainty_score": fact_certainty_score,
            "root_cause_hypothesis": root_cause_hypothesis
        }

