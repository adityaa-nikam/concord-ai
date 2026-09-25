from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.base import get_db
from app.models.domain import AuditLog
from app.schemas.case import AuditLogSchema

router = APIRouter(prefix="/audit", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogSchema])
def get_audit_logs(
    case_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    query = db.query(AuditLog)
    if case_id:
        query = query.filter(AuditLog.case_id == case_id)
    return query.order_by(desc(AuditLog.created_at)).offset(skip).limit(limit).all()
