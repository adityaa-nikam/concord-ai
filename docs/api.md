# TAT Guardian (CONCORD AI) - REST API Documentation

Base URL: `http://localhost:8000/api`

---

## 1. System Health

### `GET /health`
Returns current system operational status and database connection state.

**Response `200 OK`**:
```json
{
  "status": "online",
  "service": "TAT Guardian (CONCORD AI)",
  "version": "1.0.0",
  "environment": "development",
  "database": "healthy"
}
```

---

## 2. Case Management

### `GET /api/cases`
Lists dispute cases with optional filtering and search.

**Query Parameters**:
- `status` (optional): Filter by `NEW`, `INVESTIGATING`, `POLICY_CHECK`, `RESOLVED`, `ESCALATED`.
- `search` (optional): Search term for Case ID, UTR, customer name, or UPI handle.
- `skip` (int): Offset (default `0`).
- `limit` (int): Page size (default `20`).

**Response `200 OK`**:
```json
{
  "total": 4,
  "active_cases_count": 3,
  "escalated_count": 1,
  "resolved_count": 1,
  "cases": [
    {
      "id": "case-001",
      "case_number": "CAS-2026-0001",
      "status": "NEW",
      "priority": "HIGH",
      "issue_description": "₹2,400 was deducted from my account, but the merchant did not receive.",
      "customer_name": "Rajesh Kumar",
      "customer_upi": "rajesh@paytm",
      "transaction_utr": "426189012345",
      "amount": 2400.0,
      "tat_deadline": "2026-09-25T16:00:00Z",
      "created_at": "2026-09-24T18:00:00Z"
    }
  ]
}
```

### `GET /api/cases/{case_id}`
Retrieves complete details for a single dispute case including customer, transaction diagnostics, agent runs, actions, and audit logs.

### `POST /api/cases`
Creates a new dispute case.

**Request Body**:
```json
{
  "customer_upi": "rajesh@paytm",
  "transaction_utr": "426189012345",
  "issue_description": "₹2,400 deducted, receiver not credited",
  "priority": "HIGH"
}
```

### `POST /api/cases/{case_id}/escalate`
Triggers manual human ops escalation for a case.

---

## 3. Agent Operations

### `POST /api/agent/run/{case_id}`
Triggers full execution of the LangGraph agent state machine for a specific case.

**Response `200 OK`**:
```json
{
  "id": "run-uuid",
  "case_id": "case-001",
  "status": "SUCCESS",
  "steps_completed": 7,
  "started_at": "2026-09-24T18:00:00Z",
  "completed_at": "2026-09-24T18:00:02Z",
  "tool_calls": [...]
}
```

### `GET /api/agent/runs/{run_id}`
Retrieves agent run execution details and tool call logs.

---

## 4. Resolution Actions

### `POST /api/actions/reversal`
Executes an auto-reversal action for a transaction through the mock reversal engine.
