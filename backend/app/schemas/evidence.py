from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class EvidenceReliability:
    SYSTEM_OF_RECORD = "SYSTEM_OF_RECORD"           # Authoritative CBS / Bank / Reversal Engine
    SECONDARY_DERIVED = "SECONDARY_DERIVED"         # Gateway API or polling response
    UNVERIFIED_CUSTOMER_CLAIM = "UNVERIFIED_CUSTOMER_CLAIM" # Text in customer complaint


class EvidenceFreshness:
    CURRENT = "CURRENT"   # Freshly fetched in active investigation
    STALE = "STALE"       # Older query or cached response
    UNKNOWN = "UNKNOWN"   # Freshness cannot be determined


class EvidenceItem(BaseModel):
    source: str           # gateway, ledger, beneficiary, reversal, transaction, customer_complaint
    field: str            # status, debit_status, credit_status, is_reversed, amount, npci_status
    value: Any            # Value or "UNKNOWN" / "MISSING" / "STALE"
    timestamp: str        # Observed ISO timestamp
    reliability: str      # SYSTEM_OF_RECORD, SECONDARY_DERIVED, UNVERIFIED_CUSTOMER_CLAIM
    freshness: str        # CURRENT, STALE, UNKNOWN
    reference_id: Optional[str] = None
    notes: Optional[str] = None


class NormalizedEvidenceSet(BaseModel):
    items: List[EvidenceItem]
    transaction_type: str  # UPI_TRANSFER vs UPI_MERCHANT_PAYMENT
    missing_fields: List[str]
    system_of_record_count: int
    unverified_claim_count: int
    has_stale_data: bool
