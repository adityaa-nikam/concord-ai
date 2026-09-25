import uuid
from typing import Dict, Any
import logging
from sqlalchemy.orm import Session
from app.models.domain import Notification, AuditLog, Customer
from app.models.enums import NotificationChannel

logger = logging.getLogger("tat_guardian.services.notification")


class NotificationService:
    """Mock Customer Notification service for SMS / WhatsApp dispatch."""

    def __init__(self, db: Session):
        self.db = db

    def send_customer_notification(
        self,
        customer_id: str,
        case_id: str,
        message: str,
        channel: NotificationChannel = NotificationChannel.SMS
    ) -> Dict[str, Any]:
        customer = self.db.query(Customer).filter(Customer.id == customer_id).first()
        if not customer:
            return {"success": False, "error": f"Customer {customer_id} not found"}

        notification_id = str(uuid.uuid4())
        notif = Notification(
            id=notification_id,
            customer_id=customer_id,
            case_id=case_id,
            channel=channel,
            message=message,
            status="SENT"
        )
        self.db.add(notif)

        audit = AuditLog(
            id=str(uuid.uuid4()),
            case_id=case_id,
            event_type="CUSTOMER_NOTIFIED",
            actor="CONCORD_AI",
            details={"channel": channel.value, "phone": customer.phone, "message": message}
        )
        self.db.add(audit)
        self.db.commit()

        logger.info(f"Notification sent to customer {customer.phone} via {channel.value}")
        return {
            "success": True,
            "notification_id": notification_id,
            "channel": channel.value,
            "recipient": customer.phone,
            "message": message
        }
