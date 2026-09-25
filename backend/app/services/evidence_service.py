from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

from app.schemas.evidence import (
    EvidenceItem, NormalizedEvidenceSet, EvidenceReliability, EvidenceFreshness
)

logger = logging.getLogger("tat_guardian.services.evidence_normalization")


class EvidenceNormalizationService:
    """Service that converts tool outputs into a standard, structured NormalizedEvidenceSet."""

    @classmethod
    def normalize_evidence_set(
        cls,
        tx_data: Optional[Dict[str, Any]] = None,
        gw_data: Optional[Dict[str, Any]] = None,
        ledger_data: Optional[Dict[str, Any]] = None,
        bene_data: Optional[Dict[str, Any]] = None,
        rev_data: Optional[Dict[str, Any]] = None,
        customer_msg: Optional[str] = None,
        extracted_amount: Optional[float] = None,
        freshness_threshold_seconds: int = 3600
    ) -> NormalizedEvidenceSet:

        now = datetime.now(timezone.utc)
        now_iso = now.isoformat()
        items: List[EvidenceItem] = []
        missing_fields: List[str] = []
        has_stale_data = False

        ref_id = tx_data.get("utr") if tx_data else None

        # Helper to check timestamp freshness
        def check_freshness(ts_str: Optional[str]) -> str:
            nonlocal has_stale_data
            if not ts_str:
                return EvidenceFreshness.UNKNOWN
            try:
                obs_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if obs_dt.tzinfo is None:
                    obs_dt = obs_dt.replace(tzinfo=timezone.utc)
                diff = (now - obs_dt).total_seconds()
                if diff > freshness_threshold_seconds:
                    has_stale_data = True
                    return EvidenceFreshness.STALE
                return EvidenceFreshness.CURRENT
            except Exception:
                return EvidenceFreshness.UNKNOWN

        # 1. Customer Complaint Text (Unverified Claim)
        if customer_msg:
            items.append(EvidenceItem(
                source="customer_complaint",
                field="issue_description",
                value=customer_msg,
                timestamp=now_iso,
                reliability=EvidenceReliability.UNVERIFIED_CUSTOMER_CLAIM,
                freshness=EvidenceFreshness.CURRENT,
                reference_id=ref_id,
                notes="Unverified customer complaint claim text"
            ))
        else:
            missing_fields.append("customer_complaint.issue_description")

        if extracted_amount is not None:
            items.append(EvidenceItem(
                source="customer_complaint",
                field="extracted_amount",
                value=extracted_amount,
                timestamp=now_iso,
                reliability=EvidenceReliability.UNVERIFIED_CUSTOMER_CLAIM,
                freshness=EvidenceFreshness.CURRENT,
                reference_id=ref_id,
                notes="Claim amount extracted from customer message"
            ))

        # Determine transaction type (UPI_TRANSFER vs UPI_MERCHANT_PAYMENT)
        payee_upi = tx_data.get("payee_upi", "") if tx_data else ""
        tx_type = "UPI_MERCHANT_PAYMENT" if "merchant" in payee_upi.lower() or "swiggy" in payee_upi.lower() or "store" in payee_upi.lower() else "UPI_TRANSFER"

        # 2. Transaction Service (System of Record)
        if tx_data:
            tx_ts = tx_data.get("created_at") or now_iso
            items.append(EvidenceItem(
                source="transaction",
                field="amount",
                value=tx_data.get("amount", "MISSING"),
                timestamp=tx_ts,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=check_freshness(tx_ts),
                reference_id=ref_id,
                notes="System transaction record amount"
            ))
            items.append(EvidenceItem(
                source="transaction",
                field="status",
                value=(tx_data.get("status") or "UNKNOWN").upper(),
                timestamp=tx_ts,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=check_freshness(tx_ts),
                reference_id=ref_id,
                notes="System transaction status"
            ))
        else:
            missing_fields.append("transaction.amount")
            missing_fields.append("transaction.status")
            items.append(EvidenceItem(
                source="transaction",
                field="status",
                value="MISSING",
                timestamp=now_iso,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=EvidenceFreshness.UNKNOWN,
                reference_id=ref_id
            ))

        # 3. Payment Gateway (Secondary Derived)
        if gw_data and gw_data.get("found"):
            gw_ts = gw_data.get("queried_at") or now_iso
            gw_stat = (gw_data.get("gateway_status") or "UNKNOWN").upper()
            npci_stat = (gw_data.get("npci_status") or "UNKNOWN").upper()

            items.append(EvidenceItem(
                source="gateway",
                field="gateway_status",
                value=gw_stat,
                timestamp=gw_ts,
                reliability=EvidenceReliability.SECONDARY_DERIVED,
                freshness=check_freshness(gw_ts),
                reference_id=ref_id,
                notes="Paytm Payment Gateway API status"
            ))
            items.append(EvidenceItem(
                source="gateway",
                field="npci_status",
                value=npci_stat,
                timestamp=gw_ts,
                reliability=EvidenceReliability.SECONDARY_DERIVED,
                freshness=check_freshness(gw_ts),
                reference_id=ref_id,
                notes="NPCI clearing switch status"
            ))
        else:
            missing_fields.append("gateway.gateway_status")
            items.append(EvidenceItem(
                source="gateway",
                field="gateway_status",
                value="MISSING",
                timestamp=now_iso,
                reliability=EvidenceReliability.SECONDARY_DERIVED,
                freshness=EvidenceFreshness.UNKNOWN,
                reference_id=ref_id
            ))

        # 4. Core Banking Ledger (System of Record for Remitter)
        if ledger_data and ledger_data.get("found"):
            led_ts = ledger_data.get("queried_at") or now_iso
            deb_stat = (ledger_data.get("debit_status") or "UNKNOWN").upper()
            items.append(EvidenceItem(
                source="ledger",
                field="debit_status",
                value=deb_stat,
                timestamp=led_ts,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=check_freshness(led_ts),
                reference_id=ref_id,
                notes="Remitter Core Banking CBS debit status"
            ))
        else:
            missing_fields.append("ledger.debit_status")
            items.append(EvidenceItem(
                source="ledger",
                field="debit_status",
                value="MISSING",
                timestamp=now_iso,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=EvidenceFreshness.UNKNOWN,
                reference_id=ref_id
            ))

        # 5. Beneficiary Bank (System of Record for Payee)
        if bene_data and bene_data.get("found"):
            bene_ts = bene_data.get("queried_at") or now_iso
            cred_stat = (bene_data.get("credit_status") or "UNKNOWN").upper()
            items.append(EvidenceItem(
                source="beneficiary",
                field="credit_status",
                value=cred_stat,
                timestamp=bene_ts,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=check_freshness(bene_ts),
                reference_id=ref_id,
                notes="Beneficiary Bank CBS credit status"
            ))
        else:
            missing_fields.append("beneficiary.credit_status")
            items.append(EvidenceItem(
                source="beneficiary",
                field="credit_status",
                value="UNKNOWN",
                timestamp=now_iso,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=EvidenceFreshness.UNKNOWN,
                reference_id=ref_id
            ))

        # 6. Reversal Switch (System of Record for Reversal State)
        if rev_data and rev_data.get("found"):
            rev_ts = rev_data.get("queried_at") or now_iso
            rev_stat = (rev_data.get("status") or "NOT_INITIATED").upper()
            items.append(EvidenceItem(
                source="reversal",
                field="reversal_status",
                value=rev_stat,
                timestamp=rev_ts,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=check_freshness(rev_ts),
                reference_id=ref_id,
                notes="Paytm Idempotent Reversal Engine status"
            ))
        else:
            items.append(EvidenceItem(
                source="reversal",
                field="reversal_status",
                value="NOT_INITIATED",
                timestamp=now_iso,
                reliability=EvidenceReliability.SYSTEM_OF_RECORD,
                freshness=EvidenceFreshness.CURRENT,
                reference_id=ref_id
            ))

        sor_count = sum(1 for i in items if i.reliability == EvidenceReliability.SYSTEM_OF_RECORD)
        claim_count = sum(1 for i in items if i.reliability == EvidenceReliability.UNVERIFIED_CUSTOMER_CLAIM)

        logger.info(f"Evidence normalized: {len(items)} items, type={tx_type}, sor={sor_count}, missing={len(missing_fields)}")

        return NormalizedEvidenceSet(
            items=items,
            transaction_type=tx_type,
            missing_fields=missing_fields,
            system_of_record_count=sor_count,
            unverified_claim_count=claim_count,
            has_stale_data=has_stale_data
        )
