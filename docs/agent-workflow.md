# CONCORD AI - Autonomous Resolution Engine Workflow

## Lifecycle State Machine

```
               [ Complaint Received ]
                         │
                         ▼
                   ┌───────────┐
                   │   INTAKE  │  ──> Fetch Customer & Transaction Metadata
                   └───────────┘
                         │
                         ▼
                 ┌───────────────┐
                 │   UNDERSTAND  │  ──> Convert Complaint Text to Structured Intent & NLU Payload
                 └───────────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │     INVESTIGATE     │  ──> Multi-point Status Tool Queries:
              └─────────────────────┘      • get_payment_gateway_status()
                         │                 • get_ledger_status()
                         │                 • get_beneficiary_status()
                         │                 • get_reversal_status()
                         ▼
               ┌──────────────────┐
               │    RECONCILE     │  ──> Multi-Source Cross-System Conflict Detection
               └──────────────────┘
                         │
                         ▼
                ┌────────────────┐
                │  POLICY CHECK  │  ──> Evaluate NPCI TAT Guidelines (TATPolicyEngine)
                └────────────────┘
                         │
                         ▼
                 ┌──────────────┐
                 │   DECISION   │
                 └──────────────┘
               /    /        \    \
              /    /          \    \
             /    /            \    \
            ▼    ▼              ▼    ▼
     ┌────────┐ ┌──────┐ ┌────────────┐ ┌────────────┐
     │ ACTION │ │ WAIT │ │ RESOLUTION │ │ ESCALATION │ ──> Human Ops Tier 2 (with Escalation Packet)
     └────────┘ └──────┘ └────────────┘ └────────────┘
         │
         ▼
  ┌──────────────┐
  │ VERIFICATION │ ──> Re-query get_reversal_status()
  └──────────────┘
         │
         ▼
  ┌────────────┐
  │ RESOLUTION │ ──> Dispatch Customer SMS/WhatsApp & Close Case
  └────────────┘
```

---

## Detailed Step Breakdown

### Step 1: Intake (`intake_node`)
- Loads case metadata and raw customer complaint text.
- Invokes `get_transaction(transaction_id)` to retrieve payment reference data.

### Step 2: Understand (`understand_node`)
- Uses `CustomerComplaintUnderstandEngine` to convert unstructured complaint text into structured NLU fields (`issue_type`, `extracted_amount`, `extracted_intent`, `confidence`).

### Step 3: Investigate (`investigate_node`)
- Queries 4 independent payment systems:
  1. Payment Gateway (`get_payment_gateway_status`)
  2. Remitter Bank Core Banking Ledger (`get_ledger_status`)
  3. Beneficiary Bank Switch (`get_beneficiary_status`)
  4. Auto-Reversal Switch (`get_reversal_status`)

### Step 4: Reconcile (`reconcile_node`) — *Core Differentiator*
- Analyzes independent diagnostic state vectors using `PaymentEvidenceReconciler`.
- Detects cross-system operational conflicts:
  - `GATEWAY_LEDGER_MISMATCH`: Gateway status `PENDING` vs Bank Ledger `DEBITED` or `ON_HOLD`.
  - `DEBITED_BENEFICIARY_UNCREDITED`: Remitter ledger `DEBITED` vs Beneficiary bank `NOT_CREDITED`.
  - `PAYMENT_ALREADY_CREDITED`: Remitter ledger `DEBITED` vs Beneficiary bank `CREDITED`.
  - `REVERSAL_ALREADY_COMPLETED`: Remitter ledger `REVERSED`.
  - `INCONSISTENT_BANK_HOLD`: Debit status `ON_HOLD` or NPCI status `UNKNOWN`.

### Step 5: Policy Check (`policy_check_node`)
- Evaluates reconciled evidence against NPCI TAT Rules (`TATPolicyEngine`):
  - `DEBITED_BENEFICIARY_UNCREDITED` $\rightarrow$ `AUTO_REVERSAL` (under Policy Code `TAT_P101_AUTO_REVERSAL`)
  - `GATEWAY_LEDGER_MISMATCH` / Pending buffer $\rightarrow$ `WAIT_AND_MONITOR` (under Policy Code `TAT_P102_WAIT_CLEARING_BUFFER`)
  - Inconsistent Hold / Missing Evidence $\rightarrow$ `ESCALATE_TO_HUMAN` (under Policy Code `TAT_P103_AMBIGUOUS_ESCALATION`)
  - Already Credited / Already Reversed $\rightarrow$ `NOTIFY_AND_CLOSE`

### Step 6: Decision (`decision_node`)
- Routes execution flow to `action_node`, `wait_node`, `resolution_node`, or `escalation_node`.

### Step 7: Action (`action_node`)
- Invokes `initiate_reversal` tool via controlled tool interface.

### Step 8: Verification (`verification_node`)
- Re-queries `get_reversal_status` to verify credit posting.

### Step 9: Resolution (`resolution_node`)
- Dispatches customer notification via `send_customer_notification` tool and sets status to `RESOLVED`.

### Step 10: Escalation (`escalation_node`)
- Generates a structured `escalation_packet` containing full diagnostic snapshot & conflict details for Ops Tier 2 queue.
