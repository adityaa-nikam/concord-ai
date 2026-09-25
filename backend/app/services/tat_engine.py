from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional
from pydantic import BaseModel
import logging

from app.policies.schemas import PolicyRecordSchema

logger = logging.getLogger("tat_guardian.services.tat_engine")


class TATEvaluationResult(BaseModel):
    tat_status: str               # WITHIN_TAT, TAT_REACHED, TAT_EXCEEDED, UNKNOWN
    tat_rule: str                 # T_PLUS_1, T_PLUS_5, T_MINUS_BUFFER, MANUAL_REVIEW
    max_tat_hours: int
    elapsed_time_hours: float
    remaining_time_hours: float
    deadline_iso: str
    compensation_applicable: bool
    compensation_amount: float     # ₹100/day for RBI regulatory delay beyond T+1
    delay_days: int


class DeterministicTATEngine:
    """Deterministic TAT service with clock dependency injection for accurate time & compensation calculations."""

    @classmethod
    def evaluate_tat(
        cls,
        policy: PolicyRecordSchema,
        tx_created_at: Optional[datetime],
        current_time: Optional[datetime] = None,
        transaction_type: str = "UPI_TRANSFER"
    ) -> TATEvaluationResult:

        if not tx_created_at:
            now_iso = (current_time or datetime.now(timezone.utc)).isoformat()
            return TATEvaluationResult(
                tat_status="UNKNOWN",
                tat_rule=policy.tat_rule,
                max_tat_hours=24,
                elapsed_time_hours=0.0,
                remaining_time_hours=0.0,
                deadline_iso=now_iso,
                compensation_applicable=False,
                compensation_amount=0.0,
                delay_days=0
            )

        now = current_time or datetime.now(timezone.utc)

        # Ensure timezone-aware datetimes
        if tx_created_at.tzinfo is None:
            tx_created_at = tx_created_at.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # Max TAT hours based on policy rule
        if policy.tat_rule == "T_PLUS_1":
            max_hours = 24
        elif policy.tat_rule == "T_PLUS_5":
            max_hours = 120
        elif policy.tat_rule == "T_MINUS_BUFFER":
            max_hours = 1
        else:
            max_hours = 48

        deadline_dt = tx_created_at + timedelta(hours=max_hours)
        elapsed_sec = (now - tx_created_at).total_seconds()
        elapsed_hours = max(0.0, round(elapsed_sec / 3600.0, 2))
        remaining_hours = round((deadline_dt - now).total_seconds() / 3600.0, 2)

        # Classify status
        if elapsed_hours < max_hours:
            status = "WITHIN_TAT"
        elif elapsed_hours == max_hours:
            status = "TAT_REACHED"
        else:
            status = "TAT_EXCEEDED"

        # Calculate RBI compensation for delayed fund transfers beyond T+1 (₹100 / day)
        comp_applicable = False
        comp_amount = 0.0
        delay_days = 0

        if status == "TAT_EXCEEDED" and policy.source_type == "REGULATORY" and policy.compensation_rule:
            delay_sec = (now - deadline_dt).total_seconds()
            delay_days = max(1, int(delay_sec // (24 * 3600)) + 1)
            comp_applicable = True
            comp_amount = delay_days * policy.compensation_rule.rate_per_day

        return TATEvaluationResult(
            tat_status=status,
            tat_rule=policy.tat_rule,
            max_tat_hours=max_hours,
            elapsed_time_hours=elapsed_hours,
            remaining_time_hours=remaining_hours,
            deadline_iso=deadline_dt.isoformat(),
            compensation_applicable=comp_applicable,
            compensation_amount=comp_amount,
            delay_days=delay_days
        )
