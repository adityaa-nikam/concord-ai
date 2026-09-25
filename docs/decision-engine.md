# Concord-AI Decision Support Engine & Policy Gate Security

## Overview

The Concord-AI Decision Support Engine & Policy Gate establishes a double-authorization security barrier that governs all agent resolution actions. The engine enforces standard machine-readable reason codes, strict prompt injection defenses, and multi-source post-action verification.

---

## 1. Decision Taxonomy & Allowlist

The decision layer produces one of four primary decision outcomes:

| Decision | Allowed Actions | Description |
|---|---|---|
| `ACT` | `INITIATE_REVERSAL` | Policy authorizes automated reversal execution via controlled gateway. |
| `WAIT` | `WAIT_AND_MONITOR` | Transaction is pending consistently within TAT clearing window. |
| `ESCALATE` | `CREATE_ESCALATION` | Cross-system conflict, high-value transaction, or verification failure requiring Tier 2 Ops. |
| `RESOLVE` | `SEND_NOTIFICATION` | Case is already resolved prior or verified completed. |

---

## 2. Standard Machine-Readable Reason Codes

All decisions map to standard, non-arbitrary `ReasonCodes`:

| Reason Code | Category | Explanation |
|---|---|---|
| `ELIGIBLE_EXCEPTION` | Authorization | Policy permits auto-reversal for cross-system conflict. |
| `PENDING_WITHIN_TAT` | Buffer State | Transaction within T+1 / clearing window. |
| `ALREADY_RESOLVED` | Idempotency | Transaction was already reversed previously. |
| `UNRESOLVED_CROSS_SYSTEM_CONFLICT` | Ambiguity | Complex state mismatch requiring human review. |
| `INSUFFICIENT_EVIDENCE` | Telemetry Failure | Essential tool signals missing or unconfirmed. |
| `POLICY_UNAVAILABLE` | Governance | Applicable policy document missing or invalid. |
| `ACTION_NOT_PERMITTED` | Policy Gate | Policy gate rejected proposal. |
| `DUPLICATE_ACTION` | Security | Action with same idempotency key already executed. |
| `VERIFICATION_FAILED` | Outcome Check | Post-action verification failed. |
| `HIGH_VALUE_THRESHOLD_EXCEEDED` | Risk Control | Amount > ₹50,000 threshold for automated resolution. |
| `PROMPT_INJECTION_ATTEMPT_DETECTED` | Security | Untrusted customer text attempted prompt injection. |

---

## 3. Double-Authorization Workflow: Policy Gate & Action Gateway

No financial action is executed directly by LLM reasoning. Every action proposal undergoes strict double-authorization:

```
LLM / Decision Engine Proposal
            │
            ▼
┌───────────────────────────────┐
│     Policy Gate Validation    │  ◄── Checks: Policy Allowlist, High-Value Threshold,
└───────────────┬───────────────┘      Duplicate Action Key, Evidence Completeness
                │
         Passed │ Rejected
                ├───► ESCALATE TO OPS
                ▼
┌───────────────────────────────┐
│   Action Gateway Execution    │  ◄── Enforces Idempotency Keys (REVERSAL:tx_id)
└───────────────┬───────────────┘
                │
                ▼
┌───────────────────────────────┐
│   Post-Action Verification    │  ◄── Re-queries Core Ledger & Reversal Engine
└───────────────┬───────────────┘
                │
         Passed │ Failed
                ├───► ESCALATE TO OPS (VERIFICATION_FAILED)
                ▼
            RESOLVED
```

---

## 4. Prompt Injection Defense Architecture

Concord-AI strictly separates **Untrusted User Inputs** from **Trusted System Context**:

- **Customer Messages** (`customer_message`): Treated as `UNTRUSTED_USER_TEXT`.
- **System Telemetry & Policy Rules**: Treated as `SYSTEM_OF_RECORD` / `REGULATORY`.
- **Defense Mechanism**: `understand_node` detects prompt injection keywords (e.g., `"ignore policy"`, `"override"`, `"refund me twice"`). When detected:
  1. `prompt_injection_detected` flag is set to `True`.
  2. `DecisionSupportService` immediately overrides decision to `ESCALATE`.
  3. Reason code is set to `PROMPT_INJECTION_ATTEMPT_DETECTED`.
  4. System logs security audit event and routes case safely to human ops without executing financial actions.

---

## 5. Confidence Score Limitations vs. Regulatory Governance

Concord-AI distinguishes between `model_confidence` and `action_eligibility`:

- **Model Confidence**: Statistical confidence score (e.g., 0.95) measuring NLU parsing accuracy.
- **Action Eligibility**: Strict binary governance rule (`AUTO_REVERSAL_PERMITTED` vs `PROHIBITED`).
- **Safety Guarantee**: High model confidence (e.g., 99%) NEVER overrides policy prohibitions, TAT windows, or verification failures. Policy remains the sole authoritative gatekeeper for financial execution.
