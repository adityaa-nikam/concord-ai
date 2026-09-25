import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, DateTime, ForeignKey, Text, Enum as SQLEnum, JSON, Boolean, Integer
)
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.enums import (
    CaseStatus, TransactionStatus, ActionStatus, ActionType,
    NotificationChannel, PriorityLevel
)


def generate_uuid():
    return str(uuid.uuid4())


def utc_now():
    return datetime.now(timezone.utc)


class Customer(Base):
    __tablename__ = "customers"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)
    email = Column(String(100), nullable=True)
    upi_id = Column(String(100), nullable=False, unique=True)
    created_at = Column(DateTime, default=utc_now)

    cases = relationship("Case", back_populates="customer", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="customer")


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    utr = Column(String(36), nullable=False, unique=True, index=True)
    amount = Column(Float, nullable=False)
    payer_upi = Column(String(100), nullable=False)
    payee_upi = Column(String(100), nullable=False)
    status = Column(SQLEnum(TransactionStatus), nullable=False, default=TransactionStatus.PENDING)
    failure_reason = Column(String(255), nullable=True)
    remitter_bank = Column(String(50), nullable=False, default="Paytm Payments Bank")
    beneficiary_bank = Column(String(50), nullable=False, default="State Bank of India")
    created_at = Column(DateTime, default=utc_now)
    
    # Mock status check indicators
    remitter_debit_status = Column(String(20), nullable=False, default="DEBITED")
    beneficiary_credit_status = Column(String(20), nullable=False, default="NOT_CREDITED")
    gateway_status = Column(String(20), nullable=False, default="SUCCESS")
    npci_status = Column(String(20), nullable=False, default="TIMEOUT")

    cases = relationship("Case", back_populates="transaction")


class Case(Base):
    __tablename__ = "cases"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_number = Column(String(20), nullable=False, unique=True, index=True)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    transaction_id = Column(String(36), ForeignKey("transactions.id"), nullable=False)
    issue_description = Column(Text, nullable=False)
    status = Column(SQLEnum(CaseStatus), nullable=False, default=CaseStatus.NEW, index=True)
    priority = Column(SQLEnum(PriorityLevel), nullable=False, default=PriorityLevel.MEDIUM)
    tat_deadline = Column(DateTime, nullable=False)
    resolution_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now)

    # Relationships
    customer = relationship("Customer", back_populates="cases")
    transaction = relationship("Transaction", back_populates="cases")
    agent_runs = relationship("AgentRun", back_populates="case", cascade="all, delete-orphan")
    actions = relationship("Action", back_populates="case", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="case", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="case", cascade="all, delete-orphan")


class AgentRun(Base):
    __tablename__ = "agent_runs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    status = Column(String(20), nullable=False, default="RUNNING")
    steps_completed = Column(Integer, default=0)
    started_at = Column(DateTime, default=utc_now)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    case = relationship("Case", back_populates="agent_runs")
    tool_calls = relationship("ToolCall", back_populates="agent_run", cascade="all, delete-orphan")


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    agent_run_id = Column(String(36), ForeignKey("agent_runs.id"), nullable=False)
    tool_name = Column(String(100), nullable=False)
    input_payload = Column(JSON, nullable=True)
    output_payload = Column(JSON, nullable=True)
    status = Column(String(20), nullable=False, default="SUCCESS")
    created_at = Column(DateTime, default=utc_now)

    agent_run = relationship("AgentRun", back_populates="tool_calls")


class Action(Base):
    __tablename__ = "actions"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    action_type = Column(SQLEnum(ActionType), nullable=False)
    status = Column(SQLEnum(ActionStatus), nullable=False, default=ActionStatus.INITIATED)
    initiated_by = Column(String(50), nullable=False, default="CONCORD_AI")
    payload = Column(JSON, nullable=True)
    result_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="actions")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    event_type = Column(String(100), nullable=False)
    actor = Column(String(50), nullable=False, default="CONCORD_AI")
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=utc_now)

    case = relationship("Case", back_populates="audit_logs")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    customer_id = Column(String(36), ForeignKey("customers.id"), nullable=False)
    case_id = Column(String(36), ForeignKey("cases.id"), nullable=False)
    channel = Column(SQLEnum(NotificationChannel), nullable=False, default=NotificationChannel.SMS)
    message = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="SENT")
    sent_at = Column(DateTime, default=utc_now)

    customer = relationship("Customer", back_populates="notifications")
    case = relationship("Case", back_populates="notifications")


class PolicyRule(Base):
    __tablename__ = "policy_rules"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    code = Column(String(50), nullable=False, unique=True)
    name = Column(String(100), nullable=False)
    max_tat_hours = Column(Integer, nullable=False, default=24)
    conditions = Column(JSON, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=utc_now)

