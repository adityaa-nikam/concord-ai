from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.base import get_db
from app.models.domain import Case
from app.models.enums import CaseStatus
from app.schemas.case import CaseDetailSchema

router = APIRouter(prefix="/escalations", tags=["Escalations"])


@router.get("", response_model=List[CaseDetailSchema])
def list_escalated_cases(db: Session = Depends(get_db)):
    cases = db.query(Case).filter(
        Case.status == CaseStatus.ESCALATED
    ).order_by(desc(Case.updated_at)).all()
    return cases
