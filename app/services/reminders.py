import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.models.tenant import Tenant
from app.services.notifications import customer_language, notify_barber, resolve_phone_number_id
from app.services.whatsapp_client import send_whatsapp_template_message

logger = logging.getLogger(__name__)

# Must match the name of the template approved in WhatsApp Manager.
REMINDER_TEMPLATE_NAME = "appointment_reminder"

# The app's internal language codes (ar/he/en) vs. the exact language
# codes WhatsApp templates are registered under - Meta splits English by
# region (en_US) rather than offering a bare "en".
_META_TEMPLATE_LANGUAGE = {"ar": "ar", "he": "he", "en": "en_US"}

# Static quick-reply payload configured on the template's Cancel button in
# WhatsApp Manager - the same string comes back for every reminder
# regardless of which appointment it was about, since template buttons
# aren't per-message dynamic. The actual appointment is inferred from
# who's replying (see cancel_via_reminder_button below).
CANCEL_BUTTON_PAYLOAD = "CANCEL_APPOINTMENT"


def send_due_reminders(db: Session) -> int:
    """Sends a day-before reminder (with a Cancel button) to every
    customer whose booked appointment falls tomorrow and hasn't already
    been reminded. Meant to be triggered once a day by an external
    scheduler hitting POST /api/internal/send-reminders - there's no
    in-process scheduler, since that wouldn't fire reliably on a web
    service that can spin down when idle."""
    tomorrow = date.today() + timedelta(days=1)
    day_start = datetime.combine(tomorrow, datetime.min.time())
    day_end = day_start + timedelta(days=1)

    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.status == "booked",
            Appointment.reminder_sent.is_(False),
            Appointment.start_time >= day_start,
            Appointment.start_time < day_end,
        )
        .all()
    )

    sent_count = 0
    for appointment in appointments:
        customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
        tenant = db.query(Tenant).filter(Tenant.id == appointment.tenant_id).first()
        if not customer or not tenant:
            continue

        service = db.query(Service).filter(Service.id == appointment.service_id).first()
        lang = customer_language(db, appointment.tenant_id, customer.phone)

        success = send_whatsapp_template_message(
            to=customer.phone,
            template_name=REMINDER_TEMPLATE_NAME,
            language_code=_META_TEMPLATE_LANGUAGE.get(lang, "en_US"),
            body_params=[
                tenant.name,
                service.name if service else "",
                appointment.start_time.strftime("%H:%M"),
            ],
            phone_number_id=resolve_phone_number_id(db, appointment.tenant_id),
        )

        if success:
            appointment.reminder_sent = True
            db.commit()
            sent_count += 1
        else:
            logger.warning(
                "Reminder send failed for appointment %s - will retry next run",
                appointment.id,
            )

    return sent_count


def cancel_via_reminder_button(db: Session, tenant_id: int, from_number: str) -> bool:
    """Handles a tap on a reminder's Cancel button. Since the button's
    quick-reply payload is static (see CANCEL_BUTTON_PAYLOAD), it can't
    carry a specific appointment id - the target is inferred as this
    customer's earliest still-booked, already-reminded appointment, which
    in practice is unambiguous (a customer isn't usually reminded about
    two appointments at once). Returns True if something was cancelled."""
    customer = (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == from_number)
        .first()
    )
    if not customer:
        return False

    appointment = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.customer_id == customer.id,
            Appointment.status == "booked",
            Appointment.reminder_sent.is_(True),
        )
        .order_by(Appointment.start_time)
        .first()
    )
    if not appointment:
        return False

    appointment.status = "cancelled"
    db.commit()

    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    notify_barber(
        db,
        tenant_id,
        "cancellation",
        "Appointment cancelled",
        f"{customer.name} cancelled {service.name if service else 'their appointment'} on "
        f"{appointment.start_time.strftime('%b %d at %H:%M')} (via reminder).",
        appointment_id=appointment.id,
    )
    return True
