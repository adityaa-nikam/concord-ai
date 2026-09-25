from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class CompensationRule(BaseModel):
    rate_per_day: float = 100.0
    applies_after: str = "T+1"
    max_days: Optional[int] = 30


class PolicyRecordSchema(BaseModel):
    policy_id: str
    title: str
    source: str                 # e.g., "RBI Circular RBI/2019-20/67" or "Paytm Internal Operational Rule"
    source_type: str            # REGULATORY vs PROTOTYPE_OPERATIONAL
    effective_date: str         # "2019-09-20"
    transaction_type: str       # UPI_TRANSFER vs UPI_MERCHANT_PAYMENT
    conditions: List[str]
    tat_rule: str               # T_PLUS_1, T_PLUS_5, T_MINUS_BUFFER, MANUAL_REVIEW
    allowed_actions: List[str]
    wait_conditions: List[str]
    escalation_conditions: List[str]
    verification_requirements: List[str]
    compensation_rule: Optional[CompensationRule] = None
    summary: str
    version: str = "1.0.0"
    notes: Optional[str] = None



class PolicyCitation(BaseModel):
    policy_id: str
    source: str
    source_type: str
    section: str
    retrieval_relevance: float
    content_excerpt: str
    used_for: List[str]
