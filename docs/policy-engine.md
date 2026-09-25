# Concord-AI Policy RAG & Deterministic TAT Engine

## Overview

The Concord-AI Policy Engine combines structured policy record schemas, metadata-driven Policy RAG retrieval with citation traceability, and a deterministic Turn Around Time (TAT) evaluation service. It enforces a strict separation between **System Facts** ("What happened in the databases?"), **Policy Rules** ("What actions are allowed under regulatory/operational rules?"), and **Agent Decisions** ("What action should be taken?").

---

## 1. Policy Record Schema

All policies ingested into Concord-AI follow the `PolicyRecordSchema`:

```json
{
  "policy_id": "POL-RBI-UPI-TRANSFER-T1",
  "title": "RBI Harmonisation of TAT for Failed UPI Fund Transfers",
  "source": "RBI/2019-20/67 DPSS.CO.PD No.629/02.01.014/2019-20",
  "source_type": "REGULATORY",
  "effective_date": "2019-09-20",
  "version": "1.0.0",
  "transaction_type": "UPI_TRANSFER",
  "conditions": ["Payer account debited", "Beneficiary account not credited"],
  "tat_rule": "T_PLUS_1",
  "allowed_actions": ["INITIATE_REVERSAL", "NOTIFY_CUSTOMER"],
  "wait_conditions": ["Transaction initiated within T+1 window"],
  "escalation_conditions": ["Ledger debit state on administrative hold"],
  "verification_requirements": ["Verify core ledger state", "Verify reversal transaction reference"],
  "summary": "Auto-reversal by T+1 day. Compensation of ₹100/day for delays beyond T+1."
}
```

---

## 2. Regulatory vs. Operational Policy Distinction

Concord-AI explicitly categorizes policies to prevent conflation:

### A. Regulatory Policies (`REGULATORY`)
1. **RBI UPI Transfer (P2P / Person-to-Person)**: `POL-RBI-UPI-TRANSFER-T1`
   - **TAT Rule**: T+1 Day.
   - **Compensation**: ₹100 per day for delay beyond T+1.
   - **Trigger**: Payer debited but beneficiary account not credited.
2. **RBI UPI Merchant Payment (P2M / Person-to-Merchant)**: `POL-RBI-UPI-MERCHANT-T5`
   - **TAT Rule**: T+5 Days.
   - **Compensation**: ₹100 per day for delay beyond T+5.
   - **Crucial Rule**: Merchant payment settlement failures are NOT conflated with P2P fund transfers.

### B. Prototype Operational Policies (`PROTOTYPE_OPERATIONAL`)
1. **Paytm Idempotency Guard**: `POL-PAYTM-IDEMPOTENT-RETRY` (Prevents duplicate reversal calls).
2. **Paytm High-Value Escalation**: `POL-PAYTM-HIGH-VALUE-ESCALATION` (Escalates disputes > ₹50,000 to Ops).
3. **Paytm Clearing Window Buffer**: `POL-PAYTM-CLEARING-BUFFER` (Monitors pending transactions within TAT clearing window).

---

## 3. Metadata-Filtered Policy RAG & Traceability

Policy retrieval uses deterministic metadata filtering via `PolicyRAGRetriever` before semantic matching:

- **Filter Criteria**: `transaction_type`, `reconciled_case_category`, `amount`, `debit_status`, `is_reversed`.
- **Traceability Citations**: Every decision audit log includes policy citations:

```json
{
  "policy_id": "POL-RBI-UPI-TRANSFER-T1",
  "source": "RBI/2019-20/67 DPSS.CO.PD No.629/02.01.014/2019-20",
  "source_type": "REGULATORY",
  "section": "T_PLUS_1",
  "retrieval_relevance": 0.98,
  "used_for": ["TAT_evaluation", "auto_reversal_eligibility", "compensation_calculation"]
}
```

---

## 4. Deterministic TAT Engine & Compensation Calculation

The `DeterministicTATEngine` calculates precise deadlines using an **injectable clock** (ensuring test deterministic reproducibility without relying on system wall clock):

```python
tat_result = DeterministicTATEngine.evaluate_tat(
    policy=policy_record,
    tx_created_at=tx_timestamp,
    current_time=injectable_now_clock,
    transaction_type="UPI_TRANSFER"
)
```

### Output Parameters
- `tat_status`: `WITHIN_TAT`, `TAT_REACHED`, `TAT_EXCEEDED`, `UNKNOWN`
- `max_tat_hours`: 24 hours (T+1) or 120 hours (T+5)
- `deadline_timestamp`: Target resolution deadline timestamp
- `elapsed_hours` & `remaining_hours`
- `compensation_amount`: Calculated at ₹100/day for delayed days beyond deadline
