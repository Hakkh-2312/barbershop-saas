from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.notification import Notification
from app.models.tenant import Tenant
from app.models.whatsapp_conversation import WhatsappConversation
from app.services.whatsapp_client import send_whatsapp_message


def resolve_phone_number_id(db: Session, tenant_id: int) -> str | None:
    """Each tenant can have their own connected WhatsApp number
    (Tenant.whatsapp_phone_number_id); falls back to the single legacy
    WHATSAPP_PHONE_NUMBER_ID env var for a tenant that hasn't set one -
    keeps the original single-shop setup working unchanged."""
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if tenant and tenant.whatsapp_phone_number_id:
        return tenant.whatsapp_phone_number_id
    return settings.whatsapp_phone_number_id


def customer_language(db: Session, tenant_id: int, phone_number: str) -> str:
    """A customer's preferred language, learned from a prior WhatsApp
    conversation if they have one; falls back to the bot's default for a
    customer who was only ever added through the dashboard."""
    from app.services.whatsapp_i18n import DEFAULT_LANGUAGE

    conversation = (
        db.query(WhatsappConversation)
        .filter(
            WhatsappConversation.tenant_id == tenant_id,
            WhatsappConversation.phone_number == phone_number,
        )
        .first()
    )
    return conversation.language if conversation else DEFAULT_LANGUAGE


def notify_customer(db: Session, tenant_id: int, phone_number: str, body: str) -> None:
    """Sends a plain WhatsApp text to a customer via their shop's
    connected number - used for dashboard-initiated actions (a barber
    creating/cancelling/rescheduling an appointment themselves), so the
    customer hears about it the same way they would if they'd done it
    through the bot."""
    send_whatsapp_message(
        phone_number,
        body,
        phone_number_id=resolve_phone_number_id(db, tenant_id),
    )


def notify_barber(
    db: Session,
    tenant_id: int,
    type: str,
    title: str,
    message: str,
    appointment_id: int | None = None,
) -> None:
    """Creates an in-dashboard notification for the shop owner - used for
    customer-initiated actions via WhatsApp (booking, cancelling,
    rescheduling) that the owner wouldn't otherwise know about without
    checking the dashboard themselves."""
    db.add(
        Notification(
            tenant_id=tenant_id,
            type=type,
            title=title,
            message=message,
            appointment_id=appointment_id,
        )
    )
    db.commit()
