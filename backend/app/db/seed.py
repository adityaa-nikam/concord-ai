from datetime import datetime, timedelta, timezone
import logging
from sqlalchemy.orm import Session
from app.db.base import Base, engine, SessionLocal
from app.models.domain import Customer, Transaction, Case, PolicyRule
from app.models.enums import CaseStatus, TransactionStatus, PriorityLevel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tat_guardian.db.seed")


def seed_database(db: Session):
    logger.info("Initializing database tables...")
    Base.metadata.create_all(bind=db.get_bind())

    # Check if already seeded
    if db.query(Case).first():
        logger.info("Database already contains seed data. Skipping...")
        return

    logger.info("Seeding initial policy rules...")
    policy = PolicyRule(
        id="policy-p101",
        code="TAT_P101_AUTO_REVERSAL",
        name="NPCI T+1 Auto-Reversal for Failed UPI Transactions",
        max_tat_hours=24,
        conditions={"debit": "DEBITED", "credit": "NOT_CREDITED", "npci": "TIMEOUT"},
        is_active=True
    )
    db.add(policy)

    # 1. CUSTOMERS
    cust_a = Customer(id="cust-001", name="Rajesh Kumar", phone="+91 9876543210", email="rajesh.kumar@example.com", upi_id="rajesh@paytm")
    cust_b = Customer(id="cust-002", name="Priya Sharma", phone="+91 9812345678", email="priya.sharma@example.com", upi_id="priya@upi")
    cust_c = Customer(id="cust-003", name="Amit Patel", phone="+91 9711223344", email="amit.patel@example.com", upi_id="amit@paytm")
    cust_d = Customer(id="cust-004", name="Sneha Reddy", phone="+91 9654321098", email="sneha.reddy@example.com", upi_id="sneha@axis")
    cust_e = Customer(id="cust-005", name="Vikram Singh", phone="+91 9555443322", email="vikram.singh@example.com", upi_id="vikram@paytm")

    db.add_all([cust_a, cust_b, cust_c, cust_d, cust_e])
    db.flush()

    # 2. TRANSACTIONS
    # CASE-001: Conflicting State (Gateway=SUCCESS, Ledger=PENDING, Beneficiary=NOT_CREDITED)
    tx_a = Transaction(
        id="tx-001",
        utr="426189012345",
        amount=2400.00,
        payer_upi="rajesh@paytm",
        payee_upi="merchant@paytm",
        status=TransactionStatus.PENDING,
        failure_reason="CROSS_SYSTEM_MISMATCH",
        remitter_bank="Paytm Payments Bank",
        beneficiary_bank="State Bank of India",
        remitter_debit_status="DEBITED",
        beneficiary_credit_status="NOT_CREDITED",
        gateway_status="SUCCESS",
        npci_status="TIMEOUT"
    )

    # CASE-002: Already Reversed (Gateway=FAILED, Ledger=REVERSED, Beneficiary=NOT_CREDITED)
    tx_b = Transaction(
        id="tx-002",
        utr="426189098765",
        amount=1500.00,
        payer_upi="priya@upi",
        payee_upi="swiggy@icici",
        status=TransactionStatus.REVERSED,
        failure_reason="AUTO_REVERSED_PRIOR",
        remitter_bank="ICICI Bank",
        beneficiary_bank="HDFC Bank",
        remitter_debit_status="REVERSED",
        beneficiary_credit_status="NOT_CREDITED",
        gateway_status="FAILED",
        npci_status="FAILED"
    )

    # CASE-003: Pending Within TAT (Gateway=PENDING, Ledger=PENDING, Beneficiary=UNKNOWN)
    tx_c = Transaction(
        id="tx-003",
        utr="426189777888",
        amount=500.00,
        payer_upi="sneha@axis",
        payee_upi="groceries@paytm",
        status=TransactionStatus.PENDING,
        failure_reason=None,
        remitter_bank="Axis Bank",
        beneficiary_bank="Paytm Payments Bank",
        remitter_debit_status="PENDING",
        beneficiary_credit_status="UNKNOWN",
        gateway_status="PENDING",
        npci_status="IN_PROGRESS"
    )

    # CASE-004: Inconsistent Bank Hold -> Human Escalation
    tx_d = Transaction(
        id="tx-004",
        utr="426189555666",
        amount=12000.00,
        payer_upi="amit@paytm",
        payee_upi="crypto@yesbank",
        status=TransactionStatus.PENDING,
        failure_reason="INCONSISTENT_CBS_STATE",
        remitter_bank="Paytm Payments Bank",
        beneficiary_bank="Yes Bank",
        remitter_debit_status="ON_HOLD",
        beneficiary_credit_status="NOT_CREDITED",
        gateway_status="PENDING",
        npci_status="UNKNOWN"
    )

    # CASE-005: Verification Failure Scenario (Ledger debit status stays DEBITED despite reversal call!)
    tx_e = Transaction(
        id="tx-005",
        utr="426189999000",
        amount=3500.00,
        payer_upi="vikram@paytm",
        payee_upi="electronics@paytm",
        status=TransactionStatus.PENDING,
        failure_reason="SIMULATED_LEDGER_LOCK",
        remitter_bank="Paytm Payments Bank",
        beneficiary_bank="ICICI Bank",
        remitter_debit_status="DEBITED",
        beneficiary_credit_status="NOT_CREDITED",
        gateway_status="SUCCESS",
        npci_status="TIMEOUT"
    )

    db.add_all([tx_a, tx_b, tx_c, tx_d, tx_e])
    db.flush()

    # 3. CASES
    now = datetime.now(timezone.utc)
    
    case_a = Case(
        id="case-001",
        case_number="CAS-2026-0001",
        customer_id=cust_a.id,
        transaction_id=tx_a.id,
        issue_description="₹2,400 was deducted from my account, but the merchant/receiver did not receive the money.",
        status=CaseStatus.NEW,
        priority=PriorityLevel.HIGH,
        tat_deadline=now + timedelta(hours=22)
    )

    case_b = Case(
        id="case-002",
        case_number="CAS-2026-0002",
        customer_id=cust_b.id,
        transaction_id=tx_b.id,
        issue_description="Money deducted for Swiggy order, did not reach merchant.",
        status=CaseStatus.RESOLVED,
        priority=PriorityLevel.MEDIUM,
        tat_deadline=now + timedelta(hours=18),
        resolution_summary="Auto-reversal confirmed completed."
    )

    case_c = Case(
        id="case-003",
        case_number="CAS-2026-0003",
        customer_id=cust_d.id,
        transaction_id=tx_c.id,
        issue_description="Paid for groceries 2 mins ago, seller says money not received.",
        status=CaseStatus.NEW,
        priority=PriorityLevel.LOW,
        tat_deadline=now + timedelta(hours=23)
    )

    case_d = Case(
        id="case-004",
        case_number="CAS-2026-0004",
        customer_id=cust_c.id,
        transaction_id=tx_d.id,
        issue_description="Large transfer of ₹12,000 stuck in pending state for over 4 hours.",
        status=CaseStatus.NEW,
        priority=PriorityLevel.CRITICAL,
        tat_deadline=now + timedelta(hours=14)
    )

    case_e = Case(
        id="case-005",
        case_number="CAS-2026-0005",
        customer_id=cust_e.id,
        transaction_id=tx_e.id,
        issue_description="₹3,500 deducted for electronics purchase, seller uncredited.",
        status=CaseStatus.NEW,
        priority=PriorityLevel.HIGH,
        tat_deadline=now + timedelta(hours=20)
    )

    db.add_all([case_a, case_b, case_c, case_d, case_e])
    db.commit()
    logger.info("Database successfully seeded with 5 realistic test cases (CASE-001 through CASE-005)!")


if __name__ == "__main__":
    db_session = SessionLocal()
    try:
        seed_database(db_session)
    finally:
        db_session.close()
