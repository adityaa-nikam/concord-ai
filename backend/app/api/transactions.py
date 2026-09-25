from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.base import get_db
from app.models.domain import Transaction
from app.schemas.case import TransactionSchema
from app.services.payment_gateway import PaymentGatewayService

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get("/{transaction_id}", response_model=TransactionSchema)
def get_transaction(transaction_id: str, db: Session = Depends(get_db)):
    tx = db.query(Transaction).filter(
        (Transaction.id == transaction_id) | (Transaction.utr == transaction_id)
    ).first()

    if not tx:
        raise HTTPException(status_code=404, detail=f"Transaction {transaction_id} not found")

    return tx
