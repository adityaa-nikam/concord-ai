from pydantic import BaseModel, Field
from typing import Optional, Any
from app.models.enums import ActionType


class ReversalRequestSchema(BaseModel):
    case_id: str
    transaction_id: str
    reason: str = Field(..., description="Reason for triggering UPI auto-reversal")
    initiated_by: str = Field(default="CONCORD_AI", description="System component or user triggering action")


class ActionResponseSchema(BaseModel):
    action_id: str
    case_id: str
    action_type: ActionType
    status: str
    payload: Optional[Any] = None
    result_payload: Optional[Any] = None
    message: str


class EscalationRequestSchema(BaseModel):
    case_id: str
    reason: str
    details: Optional[str] = None
