import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.db.base import get_db
from app.models.domain import Case, Customer, Transaction
from app.models.enums import CaseStatus, TransactionStatus
from app.schemas.case import (
    CaseListResponse, CaseListItemSchema, CaseDetailSchema, CaseCreateSchema
)
from app.schemas.action import EscalationRequestSchema
from app.services.escalation import EscalationService

router = APIRouter(prefix="/cases", tags=["Cases"])


@router.get("", response_model=CaseListResponse)
def list_cases(
    status: Optional[CaseStatus] = Query(None, description="Filter by case status"),
    search: Optional[str] = Query(None, description="Search by case number, UTR or customer UPI"),
    skip: int = 0,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    query = db.query(Case)

    if status:
        query = query.filter(Case.status == status)

    if search:
        search_pattern = f"%{search}%"
        query = query.join(Customer).join(Transaction).filter(
            (Case.case_number.ilike(search_pattern)) |
            (Transaction.utr.ilike(search_pattern)) |
            (Customer.upi_id.ilike(search_pattern)) |
            (Customer.name.ilike(search_pattern))
        )

    total = query.count()
    cases_orm = query.order_by(desc(Case.created_at)).offset(skip).limit(limit).all()

    # Calculate overall dashboard counts
    active_count = db.query(Case).filter(Case.status.in_([
        CaseStatus.NEW, CaseStatus.INVESTIGATING, CaseStatus.POLICY_CHECK,
        CaseStatus.ACTION_REQUIRED, CaseStatus.ACTION_IN_PROGRESS, CaseStatus.VERIFYING
    ])).count()
    escalated_count = db.query(Case).filter(Case.status == CaseStatus.ESCALATED).count()
    resolved_count = db.query(Case).filter(Case.status == CaseStatus.RESOLVED).count()

    items = []
    for c in cases_orm:
        items.append(CaseListItemSchema(
            id=c.id,
            case_number=c.case_number,
            status=c.status,
            priority=c.priority,
            issue_description=c.issue_description,
            customer_name=c.customer.name if c.customer else "Unknown",
            customer_upi=c.customer.upi_id if c.customer else "Unknown",
            transaction_utr=c.transaction.utr if c.transaction else "Unknown",
            amount=c.transaction.amount if c.transaction else 0.0,
            tat_deadline=c.tat_deadline,
            created_at=c.created_at
        ))

    return CaseListResponse(
        total=total,
        active_cases_count=active_count,
        escalated_count=escalated_count,
        resolved_count=resolved_count,
        cases=items
    )


@router.get("/{case_id}", response_model=CaseDetailSchema)
def get_case_detail(case_id: str, db: Session = Depends(get_db)):
    case = db.query(Case).filter(
        (Case.id == case_id) | (Case.case_number == case_id)
    ).first()

    if not case:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    return case


@router.post("", response_model=CaseDetailSchema, status_code=status.HTTP_201_CREATED)
def create_case(req: CaseCreateSchema, db: Session = Depends(get_db)):
    # Verify/Find customer
    customer = db.query(Customer).filter(Customer.upi_id == req.customer_upi).first()
    if not customer:
        customer = Customer(
            id=str(uuid.uuid4()),
            name=req.customer_upi.split("@")[0].capitalize(),
            phone="+91 9900000000",
            upi_id=req.customer_upi
        )
        db.add(customer)
        db.flush()

    # Verify/Find transaction
    tx = db.query(Transaction).filter(Transaction.utr == req.transaction_utr).first()
    if not tx:
        tx = Transaction(
            id=str(uuid.uuid4()),
            utr=req.transaction_utr,
            amount=1000.0,
            payer_upi=req.customer_upi,
            payee_upi="merchant@paytm",
            status=TransactionStatus.PENDING,
            remitter_debit_status="DEBITED",
            beneficiary_credit_status="NOT_CREDITED",
            gateway_status="SUCCESS",
            npci_status="TIMEOUT"
        )
        db.add(tx)
        db.flush()

    count = db.query(Case).count() + 1
    case_num = f"CAS-2026-{count:04d}"

    case = Case(
        id=str(uuid.uuid4()),
        case_number=case_num,
        customer_id=customer.id,
        transaction_id=tx.id,
        issue_description=req.issue_description,
        status=CaseStatus.NEW,
        priority=req.priority,
        tat_deadline=datetime.now(timezone.utc) + timedelta(hours=24)
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


@router.post("/{case_id}/escalate")
def escalate_case(case_id: str, req: EscalationRequestSchema, db: Session = Depends(get_db)):
    esc_svc = EscalationService(db)
    res = esc_svc.create_human_escalation(
        case_id=case_id,
        reason=req.reason,
        details={"manual_notes": req.details}
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error"))
    return res
