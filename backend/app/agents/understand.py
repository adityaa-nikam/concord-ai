import re
from typing import Dict, Any, Optional, List
import logging
from sqlalchemy.orm import Session
from app.models.domain import Transaction, Case

logger = logging.getLogger("tat_guardian.agents.understand")


class CustomerComplaintUnderstandEngine:
    """NLU Understand engine for extracting intent, amounts, UTRs, and resolving missing transaction IDs."""

    @classmethod
    def parse_complaint(
        cls,
        text: str,
        case_id: str,
        db: Session,
        default_amount: Optional[float] = None,
        default_utr: Optional[str] = None
    ) -> Dict[str, Any]:
        text_lower = text.lower() if text else ""
        extracted_amount = default_amount
        extracted_utr = None
        is_ambiguous = False

        # 1. Regex Amount Extraction (₹2,400, Rs. 2400, INR 2400)
        amount_match = re.search(r'(?:₹|rs\.?|inr)\s*([\d,]+(?:\.\d{1,2})?)', text, re.IGNORECASE)
        if not amount_match:
            amount_match = re.search(r'([\d,]+)\s*(?:rupees|rs)', text, re.IGNORECASE)

        if amount_match:
            try:
                amt_str = amount_match.group(1).replace(',', '')
                extracted_amount = float(amt_str)
            except ValueError:
                pass

        # 2. UTR Extraction (12-digit numeric reference)
        utr_match = re.search(r'\b\d{12}\b', text)
        if utr_match:
            extracted_utr = utr_match.group(0)
        elif default_utr:
            extracted_utr = default_utr
        else:
            # Candidate transaction lookup from case metadata (Do NOT hallucinate!)
            case = db.query(Case).filter(Case.id == case_id).first()
            if case and case.transaction:
                extracted_utr = case.transaction.utr
            else:
                is_ambiguous = True

        # 3. Intent & Issue Type Categorization
        confidence = 0.90 if not is_ambiguous else 0.60
        if "deducted" in text_lower or "debited" in text_lower or "went through" in text_lower:
            if "not receive" in text_lower or "didn't get" in text_lower or "didn't receive" in text_lower or "not credited" in text_lower or "reach" in text_lower:
                issue_type = "DEBITED_BENEFICIARY_NOT_CREDITED"
                intent = "FAILED_UPI_DISPUTE_REVERSAL"
            elif "reversed" in text_lower or "refund" in text_lower:
                issue_type = "REVERSAL_STATUS_INQUIRY"
                intent = "CHECK_REVERSAL_CREDIT"
            else:
                issue_type = "DEBITED_UNCONFIRMED_STATUS"
                intent = "DISPUTE_DEBITED_AMOUNT"
        elif "pending" in text_lower or "stuck" in text_lower or "mins ago" in text_lower:
            issue_type = "PENDING_TRANSACTION_STATUS"
            intent = "CHECK_PENDING_PAYMENT"
        else:
            issue_type = "GENERAL_UPI_DISPUTE"
            intent = "CUSTOMER_COMPLAINT_INVESTIGATION"

        return {
            "issue_type": issue_type,
            "extracted_amount": extracted_amount,
            "extracted_utr": extracted_utr,
            "extracted_intent": intent,
            "confidence": confidence,
            "is_utr_ambiguous": is_ambiguous
        }
