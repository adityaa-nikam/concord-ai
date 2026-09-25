# Concord-AI - Ground Truth Test Scenarios Reference

This document defines the synthetic test dataset and expected ground-truth outcomes for Concord-AI (TAT Guardian).

---

## Synthetic Test Scenarios

### Scenario 1: `CASE-001` (Conflicting State $\rightarrow$ Auto Reversal & Resolve)
- **Customer Complaint**: *"₹2,400 was deducted from my account, but the merchant/receiver did not receive the money."*
- **UTR**: `426189012345`
- **Telemetry State**:
  - Payment Gateway: `SUCCESS`
  - Core Banking Ledger: `PENDING` (or `DEBITED`)
  - Beneficiary Bank: `NOT_CREDITED`
  - Reversal State: `NOT_INITIATED`
- **Reconciliation Result**: `CROSS_SYSTEM_CONFLICT` (`DEBITED_BENEFICIARY_UNCREDITED`)
- **Policy Result**: `UPI_TRANSFER_DEBITED_NOT_CREDITED` (T+1 Auto-Reversal Eligible)
- **Decision**: `ACT` $\rightarrow$ Action: `INITIATE_REVERSAL`
- **Post-Action Verification**: Re-query verifies Ledger `REVERSED` & Reversal `COMPLETED`
- **Final Case Outcome**: `RESOLVED`

---

### Scenario 2: `CASE-002` (Already Reversed $\rightarrow$ Notify & Close)
- **Customer Complaint**: *"Money deducted for Swiggy order, did not reach merchant."*
- **UTR**: `426189098765`
- **Telemetry State**:
  - Payment Gateway: `FAILED`
  - Core Banking Ledger: `REVERSED`
  - Beneficiary Bank: `NOT_CREDITED`
  - Reversal State: `COMPLETED`
- **Reconciliation Result**: `ALREADY_RESOLVED`
- **Policy Result**: `NOTIFY_AND_CLOSE` (Idempotent check prevents duplicate reversal)
- **Decision**: `NOTIFY_AND_CLOSE`
- **Final Case Outcome**: `RESOLVED`

---

### Scenario 3: `CASE-003` (Pending Within TAT $\rightarrow$ Wait & Monitor)
- **Customer Complaint**: *"Paid for groceries 2 mins ago, seller says money not received."*
- **UTR**: `426189777888`
- **Telemetry State**:
  - Payment Gateway: `PENDING`
  - Core Banking Ledger: `PENDING`
  - Beneficiary Bank: `UNKNOWN`
  - Reversal State: `NOT_INITIATED`
- **Reconciliation Result**: `PENDING_CONSISTENT`
- **Policy Result**: `UPI_CLEARING_WINDOW_BUFFER` (15-min clearing window)
- **Decision**: `WAIT` $\rightarrow$ Set monitoring state
- **Final Case Outcome**: `INVESTIGATING` (`WAIT AND MONITOR`)

---

### Scenario 4: `CASE-004` (Ambiguous Bank Hold $\rightarrow$ Escalate to Ops)
- **Customer Complaint**: *"Large transfer of ₹12,000 stuck in pending state for over 4 hours."*
- **UTR**: `426189555666`
- **Telemetry State**:
  - Payment Gateway: `PENDING`
  - Core Banking Ledger: `ON_HOLD`
  - Beneficiary Bank: `NOT_CREDITED`
  - Reversal State: `NOT_INITIATED`
- **Reconciliation Result**: `CROSS_SYSTEM_CONFLICT` (`INCONSISTENT_BANK_HOLD`)
- **Policy Result**: `UPI_MANUAL_REVIEW_FALLBACK` (Requires human ops intervention)
- **Decision**: `ESCALATE`
- **Escalation Output**: JSON Evidence Packet generated for Ops Tier 2 Queue
- **Final Case Outcome**: `ESCALATED`

---

### Scenario 5: `CASE-005` (Verification Failure Handling $\rightarrow$ Escalate to Ops)
- **Customer Complaint**: *"₹3,500 deducted for electronics purchase, seller uncredited."*
- **UTR**: `426189999000`
- **Telemetry State**:
  - Action Gateway triggers `initiate_reversal`
  - Simulated CBS Ledger stays `DEBITED` due to bank lock
- **Post-Action Verification**: Multi-source check returns `VERIFICATION_FAILED`
- **Decision**: `ESCALATE` (System does NOT trust action response blindly)
- **Final Case Outcome**: `ESCALATED`
