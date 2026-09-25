# CONCORD AI (TAT Guardian) - Architecture Specification

## Overview

**Concord-AI** is an autonomous AI operations teammate designed for Paytm Build for India AI Hackathon (Track 3: CONCORD AI). It manages, investigates, reconciles, and resolves failed/stuck UPI payment cases adhering to NPCI Turnaround Time (TAT) guidelines.

---

## Architectural & Security Boundary

```
                     +---------------------------------------+
                     |         LLM System Prompt / NLU       |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |          STRUCTURED DECISION          |
                     |   (ACT, WAIT, ESCALATE, NOTIFY)       |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |              POLICY GATE              |
                     | - Policy Allowed Check                |
                     | - Required Evidence Check             |
                     | - Idempotency Lock Check              |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |            ACTION GATEWAY             |
                     |   idempotency: REVERSAL:{txn_id}      |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |         MOCK FINTECH SERVICE          |
                     +---------------------------------------+
                                         |
                                         v
                     +---------------------------------------+
                     |     BUSINESS OUTCOME VERIFICATION     |
                     |  (Re-query Ledger & Reversal State)   |
                     +---------------------------------------+
                      /                                     \
                     v                                       v
          +--------------------+                  +--------------------+
          |  VERIFIED SUCCESS  |                  | VERIFICATION FAILS |
          |  (Mark RESOLVED)   |                  |  (Mark ESCALATED)  |
          +--------------------+                  +--------------------+
```

### Prohibited Execution Flow
The LLM is strictly prohibited from directly calling financial mutation APIs or generating SQL statements against the production database:

```
PROHIBITED:  LLM  ──>  Direct Database / Financial Mutation
```

---

## Core System Layers

1. **NLU Understand Layer (`app/agents/understand.py`)**:
   Converts customer dispute complaints into structured intent, extracted amounts, and UTR references. If UTR is missing, candidate transactions are looked up from metadata without hallucinating transaction IDs.

2. **Multi-Source Evidence Reconciler (`app/agents/reconcile.py`)**:
   Gathers telemetry from 5 independent sources (Transaction, Gateway, Core Banking Ledger, Beneficiary Bank, Reversal Switch). Reconciles evidence into 5 explicit categories (`CONSISTENT_SUCCESS`, `CROSS_SYSTEM_CONFLICT`, `ALREADY_RESOLVED`, `PENDING_CONSISTENT`, `BENEFICIARY_STATE_UNKNOWN`).

3. **Policy Knowledge Service & TAT Evaluator (`app/services/policy_service.py` & `app/policies/tat_policy.py`)**:
   Evaluates issue types against NPCI TAT Rules (`T_PLUS_1`, `T_MINUS_BUFFER`, `MANUAL_REVIEW`). Contains a deterministic TAT calculator accepting dependency-injected clocks for deterministic testing.

4. **Policy Gate & Action Gateway (`app/services/action_gateway.py`)**:
   Validates structured action proposals before execution. Enforces idempotency key `REVERSAL:{transaction_id}` to prevent duplicate financial mutations on agent retries or frontend refreshes.

5. **Business Outcome Verification (`app/agents/nodes.py`)**:
   Post-action node re-queries system services. Enforces the multi-source verification rule: `reversal_status == COMPLETED` AND `ledger_state == REVERSED`. Marks case `RESOLVED` only on verified success; marks `ESCALATED` if verification fails.
