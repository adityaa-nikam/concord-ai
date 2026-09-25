from typing import List
import logging
from app.policies.schemas import PolicyRecordSchema, CompensationRule

logger = logging.getLogger("tat_guardian.policies.loader")


class PolicyDocumentLoader:
    """Loads authoritative regulatory and prototype operational policy documents."""

    @classmethod
    def load_all_policies(cls) -> List[PolicyRecordSchema]:
        policies = [
            # 1. Authoritative RBI Regulatory Policy: UPI Transfer of Funds
            PolicyRecordSchema(
                policy_id="POL-RBI-UPI-TRANSFER-T1",
                title="RBI Harmonisation of TAT & Customer Compensation for Failed UPI Transfers",
                source="RBI Circular RBI/2019-20/67 DPSS.CO.PD No.629/02.01.014/2019-20 (Sept 20, 2019)",
                source_type="REGULATORY",
                effective_date="2019-09-20",
                transaction_type="UPI_TRANSFER",
                conditions=[
                    "Payer account debited",
                    "Beneficiary account not credited",
                    "Individual account-to-account UPI transfer of funds"
                ],
                tat_rule="T_PLUS_1",
                allowed_actions=["INITIATE_REVERSAL", "SEND_NOTIFICATION"],
                wait_conditions=["Transaction initiated within current 15-minute clearing window"],
                escalation_conditions=["Administrative hold on remitter account", "Beneficiary state unknown after T+1"],
                verification_requirements=["REVERSAL_STATUS_COMPLETED", "REMITTER_LEDGER_REVERSED"],
                compensation_rule=CompensationRule(rate_per_day=100.0, applies_after="T+1"),
                summary="Where payer account is debited but beneficiary is not credited, auto-reversal is mandated by T+1 with Rs 100/day delay compensation.",
                version="1.0.0",
                notes="Authoritative RBI regulatory framework. Mandates T+1 auto-reversal and Rs 100/day delay compensation."
            ),

            # 2. Authoritative RBI Regulatory Policy: UPI Merchant Payments
            PolicyRecordSchema(
                policy_id="POL-RBI-UPI-MERCHANT-T5",
                title="RBI Harmonisation of TAT for Failed UPI Merchant Payments",
                source="RBI Circular RBI/2019-20/67 DPSS.CO.PD No.629/02.01.014/2019-20 (Sept 20, 2019)",
                source_type="REGULATORY",
                effective_date="2019-09-20",
                transaction_type="UPI_MERCHANT_PAYMENT",
                conditions=[
                    "Payer account debited",
                    "Merchant payment status pending/unconfirmed",
                    "Merchant settlement window active"
                ],
                tat_rule="T_PLUS_5",
                allowed_actions=["WAIT_AND_MONITOR", "INITIATE_REVERSAL"],
                wait_conditions=["Within T+5 merchant reconciliation window"],
                escalation_conditions=["Merchant dispute unresolved after T+5"],
                verification_requirements=["MERCHANT_SETTLEMENT_CONFIRMATION", "REVERSAL_STATUS_COMPLETED"],
                compensation_rule=CompensationRule(rate_per_day=100.0, applies_after="T+5"),
                summary="Failed P2M merchant payments are subject to a T+5 reconciliation window before compensation applies.",
                version="1.0.0",
                notes="Authoritative RBI regulatory framework for P2M merchant transactions."
            ),

            # 3. Prototype Operational Policy: Idempotency Protection
            PolicyRecordSchema(
                policy_id="POL-PAYTM-IDEMPOTENT-RETRY",
                title="Paytm Idempotent Financial Reversal Guard",
                source="Paytm Internal FinOps Standard PAYTM/FINOPS/SEC-101",
                source_type="PROTOTYPE_OPERATIONAL",
                effective_date="2026-01-01",
                transaction_type="ALL",
                conditions=["Transaction already marked REVERSED in Core Banking or Reversal Engine"],
                tat_rule="IMMEDIATE",
                allowed_actions=["SEND_NOTIFICATION", "CLOSE_CASE"],
                wait_conditions=[],
                escalation_conditions=[],
                verification_requirements=["PREVIOUS_REVERSAL_COMPLETED"],
                compensation_rule=None,
                summary="Duplicate financial reversal calls are strictly prohibited if transaction is already reversed.",
                version="1.0.0",
                notes="Prototype operational safeguard prohibiting duplicate financial reversals."
            ),

            # 4. Prototype Operational Policy: Clearing Window Buffer
            PolicyRecordSchema(
                policy_id="POL-PAYTM-CLEARING-BUFFER",
                title="NPCI 15-Minute Clearing Buffer Rule",
                source="Paytm Internal Operational Guidelines PAYTM/OPS/BUF-01",
                source_type="PROTOTYPE_OPERATIONAL",
                effective_date="2026-01-01",
                transaction_type="ALL",
                conditions=["Pending transaction initiated within 15 minutes of dispute intake"],
                tat_rule="T_MINUS_BUFFER",
                allowed_actions=["WAIT_AND_MONITOR"],
                wait_conditions=["Elapsed time < 15 minutes"],
                escalation_conditions=[],
                verification_requirements=[],
                compensation_rule=None,
                summary="Pending transactions initiated within 15 minutes must remain in monitoring state for NPCI clearing.",
                version="1.0.0",
                notes="Prototype operational buffer to prevent premature reversal while NPCI clearing switch completes."
            ),

            # 5. Prototype Operational Policy: High-Value Escalation Threshold
            PolicyRecordSchema(
                policy_id="POL-PAYTM-HIGH-VALUE-ESCALATION",
                title="Paytm High-Value Dispute Human Escalation Limit",
                source="Paytm Internal Risk Policy PAYTM/RISK/HV-500",
                source_type="PROTOTYPE_OPERATIONAL",
                effective_date="2026-01-01",
                transaction_type="ALL",
                conditions=["Transaction amount exceeds ₹50,000 with cross-system state ambiguity"],
                tat_rule="MANUAL_REVIEW",
                allowed_actions=["CREATE_ESCALATION"],
                wait_conditions=[],
                escalation_conditions=["Amount > ₹50,000"],
                verification_requirements=[],
                compensation_rule=None,
                summary="Disputed UPI transactions exceeding Rs 50,000 require manual authorization from Tier 2 Human Ops.",
                version="1.0.0",
                notes="Prototype operational risk threshold requiring human ops authorization for large amounts."
            )
        ]

        logger.info(f"Loaded {len(policies)} policy documents ({sum(1 for p in policies if p.source_type == 'REGULATORY')} regulatory).")
        return policies
