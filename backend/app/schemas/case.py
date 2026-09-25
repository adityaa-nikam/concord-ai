from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime
from app.models.enums import CaseStatus, PriorityLevel, TransactionStatus


class CustomerSchema(BaseModel):
    id: str
    name: str
    phone: str
    email: Optional[str] = None
    upi_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TransactionSchema(BaseModel):
    id: str
    utr: str
    amount: float
    payer_upi: str
    payee_upi: str
    status: TransactionStatus
    failure_reason: Optional[str] = None
    remitter_bank: str
    beneficiary_bank: str
    remitter_debit_status: str
    beneficiary_credit_status: str
    gateway_status: str
    npci_status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ToolCallSchema(BaseModel):
    id: str
    tool_name: str
    input_payload: Optional[Any] = None
    output_payload: Optional[Any] = None
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentRunSchema(BaseModel):
    id: str
    case_id: str
    status: str
    steps_completed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    tool_calls: List[ToolCallSchema] = []

    model_config = ConfigDict(from_attributes=True)


class ActionSchema(BaseModel):
    id: str
    case_id: str
    action_type: str
    status: str
    initiated_by: str
    payload: Optional[Any] = None
    result_payload: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogSchema(BaseModel):
    id: str
    case_id: str
    event_type: str
    actor: str
    details: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationSchema(BaseModel):
    id: str
    customer_id: str
    case_id: str
    channel: str
    message: str
    status: str
    sent_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseCreateSchema(BaseModel):
    customer_upi: str = Field(..., description="Customer UPI handle e.g. user@paytm")
    transaction_utr: str = Field(..., description="12-digit UPI Transaction Reference (UTR)")
    issue_description: str = Field(..., description="Customer complaint description")
    priority: PriorityLevel = PriorityLevel.MEDIUM


class CaseDetailSchema(BaseModel):
    id: str
    case_number: str
    status: CaseStatus
    priority: PriorityLevel
    issue_description: str
    tat_deadline: datetime
    resolution_summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    customer: CustomerSchema
    transaction: TransactionSchema
    agent_runs: List[AgentRunSchema] = []
    actions: List[ActionSchema] = []
    audit_logs: List[AuditLogSchema] = []
    notifications: List[NotificationSchema] = []

    model_config = ConfigDict(from_attributes=True)


class CaseListItemSchema(BaseModel):
    id: str
    case_number: str
    status: CaseStatus
    priority: PriorityLevel
    issue_description: str
    customer_name: str
    customer_upi: str
    transaction_utr: str
    amount: float
    tat_deadline: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CaseListResponse(BaseModel):
    total: int
    active_cases_count: int
    escalated_count: int
    resolved_count: int
    cases: List[CaseListItemSchema]
