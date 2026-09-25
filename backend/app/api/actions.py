from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.schemas.action import ReversalRequestSchema, ActionResponseSchema
from app.services.reversal import ReversalService
from app.models.enums import ActionType

router = APIRouter(prefix="/actions", tags=["Resolution Actions"])


@router.post("/reversal", response_model=ActionResponseSchema)
def trigger_reversal(req: ReversalRequestSchema, db: Session = Depends(get_db)):
    rev_svc = ReversalService(db)
    res = rev_svc.initiate_reversal(
        transaction_id=req.transaction_id,
        case_id=req.case_id,
        reason=req.reason,
        initiated_by=req.initiated_by
    )

    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Reversal initiation failed"))

    return ActionResponseSchema(
        action_id=res.get("reversal_id", "REV-ACK"),
        case_id=req.case_id,
        action_type=ActionType.REVERSAL,
        status="SUCCESS",
        payload={"transaction_id": req.transaction_id, "reason": req.reason},
        result_payload=res,
        message=res.get("message", "Auto-reversal executed successfully")
    )
