# Concord-AI Evidence Normalization & Reconciliation Engine

## Overview

The Concord-AI Evidence Normalization & Reconciliation Engine is the signature capability of Concord-AI (TAT Guardian). It converts raw, heterogenous, multi-system telemetry outputs into a unified `NormalizedEvidenceSet`, deterministically reconciles system facts against system-of-record boundaries, detects cross-system conflicts, and identifies missing telemetry required for safe exception resolution.

---

## 1. Evidence Model Schema

Every piece of system telemetry collected during investigation is stored as a normalized `EvidenceItem` with standard fields:

| Field | Type | Description |
|---|---|---|
| `source` | `str` | Subsystem originating the signal (`gateway`, `ledger`, `beneficiary`, `reversal`, `customer`) |
| `field` | `str` | Specific operational status property (`gateway_status`, `debit_status`, `credit_status`, `is_reversed`) |
| `value` | `Any` | Normalized enum value (`SUCCESS`, `DEBITED`, `PENDING`, `NOT_CREDITED`, `UNKNOWN`, `MISSING`, `STALE`) |
| `timestamp` | `datetime` | ISO-8601 UTC timestamp of telemetry capture |
| `reliability` | `EvidenceReliability` | Signal authority level (`SYSTEM_OF_RECORD`, `AUTHORITATIVE_SWITCH`, `INTERMEDIARY_TELEMETRY`, `UNTRUSTED_USER_TEXT`) |
| `freshness` | `EvidenceFreshness` | Data currency evaluation (`CURRENT`, `STALE`, `UNKNOWN`) |
| `reference_id` | `Optional[str]` | UTR, transaction ID, or reversal reference identifier |

### Authority & Freshness Principles
- Core Banking Ledger (`ledger`) is the `SYSTEM_OF_RECORD` for account debits and holds.
- NPCI Switch (`gateway`) is the `AUTHORITATIVE_SWITCH` for interbank clearing.
- Customer complaints (`customer`) are classified as `UNTRUSTED_USER_TEXT` and cannot alter transaction facts.
- Freshness threshold is configurable per policy; telemetry exceeding threshold receives `STALE` freshness tag.

---

## 2. Normalization Layer

The `EvidenceNormalizationService` converts raw tool outputs (`get_transaction`, `get_gateway_status`, `get_ledger_status`, `get_beneficiary_status`, `get_reversal_status`) into a normalized set:

- **Schema Validation & Enum Mapping**: Standardizes status variants (`SUCCESS`, `SUCCESSFUL`, `COMPLETED` $\rightarrow$ `SUCCESS`).
- **Missing Value Preservation**: Missing fields are assigned `MISSING` rather than silently fallback-replaced.
- **Unconfirmed States**: Unreturned third-party switch signals receive `UNKNOWN` state.

---

## 3. Conflict Detection Taxonomy

The `DeterministicReconciliationEngine` evaluates normalized evidence sets against a deterministic conflict decision tree:

| Conflict Code | Severity | Scenario / Trigger | Resolution Action Path |
|---|---|---|---|
| `CROSS_SYSTEM_STATE_CONFLICT` | `HIGH` | Gateway = `SUCCESS`, Ledger = `DEBITED`/`PENDING`, Beneficiary = `NOT_CREDITED` | Evaluate RBI T+1 Policy $\rightarrow$ Initiate Reversal |
| `POST_ACTION_VERIFICATION_CONFLICT` | `HIGH` | Reversal API = `COMPLETED`, Ledger = `DEBITED`/`PENDING` | Fail Verification $\rightarrow$ Escalate to Tier 2 Ops |
| `INCONSISTENT_BANK_HOLD` | `CRITICAL` | Ledger = `ON_HOLD` | Disallow Mutation $\rightarrow$ Escalate to CBS Ops |
| `STALE_TELEMETRY_WARNING` | `MEDIUM` | Telemetry timestamp > Freshness Window | Request Fresh Telemetry |

### Deterministic Rules Summary
1. **Conflict A / C**: Gateway `SUCCESS` but Beneficiary `NOT_CREDITED` $\rightarrow$ `CROSS_SYSTEM_STATE_CONFLICT` (Auto-reversal candidate).
2. **Conflict B**: Gateway `FAILED` and Ledger `REVERSED` $\rightarrow$ `ALREADY_RESOLVED` (No duplicate action).
3. **Conflict D**: Gateway `PENDING` and Ledger `PENDING` $\rightarrow$ `PENDING_CONSISTENT` (Wait within clearing buffer).
4. **Conflict E**: Reversal API `COMPLETED` but Core Ledger remains `DEBITED` $\rightarrow$ `POST_ACTION_VERIFICATION_CONFLICT` (Escalate).

---

## 4. Reconciliation Output Schema

Reconciliation produces a structured `ReconciliationResult`:

```json
{
  "status": "CONFLICT",
  "reconciled_case_category": "CROSS_SYSTEM_CONFLICT",
  "conflicts": [
    {
      "conflict_detected": true,
      "conflict_type": "CROSS_SYSTEM_STATE_CONFLICT",
      "severity": "HIGH",
      "sources": ["gateway", "ledger", "beneficiary"],
      "summary": "Payment Gateway reports SUCCESS while Ledger is DEBITED and Beneficiary credit is NOT_CREDITED."
    }
  ],
  "known_facts": [
    {"source": "gateway", "fact": "gateway.gateway_status", "value": "SUCCESS", "is_system_of_record": false},
    {"source": "ledger", "fact": "ledger.debit_status", "value": "DEBITED", "is_system_of_record": true}
  ],
  "missing_information": [],
  "unresolved_questions": ["Did NPCI switch clearing time out before reaching beneficiary bank?"],
  "recommended_next_evidence": ["Retrieve applicable NPCI T+1 Auto-Reversal policy guidelines"],
  "summary": "Cross-system conflict detected: Gateway reports success while beneficiary is uncredited."
}
```

---

## 5. Iterative Investigation Loop

When critical telemetry is unconfirmed (`status == "INCOMPLETE"`), the engine identifies missing fields and bounded investigation steps:
1. Identify missing field (e.g., `beneficiary_credit_status`).
2. Dispatch permitted retrieval tool (`get_beneficiary_status()`).
3. Re-normalize evidence set and re-evaluate reconciliation state.
4. If max step limit (`MAX_INVESTIGATION_STEPS = 15`) is reached without safe resolution $\rightarrow$ Escalate to Ops.
