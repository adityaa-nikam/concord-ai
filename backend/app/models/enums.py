import enum


class CaseStatus(str, enum.Enum):
    NEW = "NEW"
    INVESTIGATING = "INVESTIGATING"
    POLICY_CHECK = "POLICY_CHECK"
    ACTION_REQUIRED = "ACTION_REQUIRED"
    ACTION_IN_PROGRESS = "ACTION_IN_PROGRESS"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class TransactionStatus(str, enum.Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    PENDING = "PENDING"
    REVERSED = "REVERSED"
    REFUND_PENDING = "REFUND_PENDING"
    REFUNDED = "REFUNDED"


class ActionStatus(str, enum.Enum):
    INITIATED = "INITIATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ActionType(str, enum.Enum):
    REVERSAL = "REVERSAL"
    ESCALATION = "ESCALATION"
    NOTIFICATION = "NOTIFICATION"
    MANUAL_OVERRIDE = "MANUAL_OVERRIDE"


class NotificationChannel(str, enum.Enum):
    SMS = "SMS"
    WHATSAPP = "WHATSAPP"
    IN_APP = "IN_APP"
    EMAIL = "EMAIL"


class PriorityLevel(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"
