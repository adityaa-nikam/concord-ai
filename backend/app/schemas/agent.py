from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class AgentRunTriggerRequest(BaseModel):
    case_id: str
    auto_execute_actions: bool = True
    notes: Optional[str] = None


class AgentRunStepDetail(BaseModel):
    node: str
    timestamp: datetime
    status: str
    details: Optional[Any] = None


class AgentRunResponse(BaseModel):
    run_id: str
    case_id: str
    status: str
    current_node: str
    steps_completed: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    investigation_summary: Optional[Any] = None
    policy_outcome: Optional[Any] = None
    decision: Optional[str] = None
    error_message: Optional[str] = None
