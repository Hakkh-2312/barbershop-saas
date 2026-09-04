import logging
from datetime import date, datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.models.customer import Customer
from app.models.service import Service
from app.models.whatsapp_conversation import WhatsappConversation
from app.services.booking import BookingError, create_booking, get_available_slots

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

WHATSAPP_API_VERSION = "v21.0"
MAX_LIST_ROWS = 10


@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(alias="hub.mode"),
    hub_verify_token: str = Query(alias="hub.verify_token"),
    hub_challenge: str = Query(alias="hub.challenge"),
):
    """Meta calls this once, synchronously, when you click "Verify and Save"
    on the webhook config page. Echoing the challenge back proves we control
    this URL and share the verify token."""
    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        return Response(content=hub_challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Webhook verification failed")


@router.post("/webhook")
async def receive_message(request: Request, db: Session = Depends(get_db)):
    """Meta POSTs here for every event we've subscribed to (currently just
    "messages"). No per-tenant routing yet - WHATSAPP_TENANT_ID says which
    single shop this WhatsApp number belongs to; mapping many numbers to
    many tenants is future work once more than one shop is on WhatsApp.
    """
    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contact_name = _extract_contact_name(value)
            for message in value.get("messages", []):
                _handle_message(db, message, contact_name)

    # Meta requires a 200 within a few seconds regardless of what we did
    # with the payload, or it will retry (and eventually disable) delivery.
    return {"status": "ok"}


def _extract_contact_name(value: dict) -> str | None:
    contacts = value.get("contacts", [])
    if contacts:
        return contacts[0].get("profile", {}).get("name")
    return None


def _handle_message(db: Session, message: dict, contact_name: str | None) -> None:
    from_number = message.get("from")
    if not from_number:
        return

    if settings.whatsapp_tenant_id is None:
        # No shop wired up to this WhatsApp number yet - keep the old
        # placeholder behavior rather than guessing which tenant it's for.
        text = message.get("text", {}).get("body", "")
        logger.info("WhatsApp message from %s: %r", from_number, text)
        send_whatsapp_message(
            to=from_number,
            body="Thanks for reaching out! Online booking via WhatsApp is coming soon.",
        )
        return

    tenant_id = settings.whatsapp_tenant_id

    selection_id = None
    if message.get("type") == "interactive":
        interactive = message.get("interactive", {})
        if interactive.get("type") == "list_reply":
            selection_id = interactive["list_reply"]["id"]

    conversation = (
        db.query(WhatsappConversation)
        .filter(
            WhatsappConversation.tenant_id == tenant_id,
            WhatsappConversation.phone_number == from_number,
        )
        .first()
    )

    if (
        selection_id
        and selection_id.startswith("service:")
        and conversation
        and conversation.state == "awaiting_service"
    ):
        _handle_service_selected(db, tenant_id, from_number, conversation, selection_id)
        return

    if (
        selection_id
        and selection_id.startswith("slot:")
        and conversation
        and conversation.state == "awaiting_slot"
    ):
        _handle_slot_selected(db, tenant_id, from_number, conversation, selection_id, contact_name)
        return

    # Anything else (first contact, stray text mid-flow, a tap on an
    # expired/stale list): (re)start by showing the service list.
    _send_service_list(db, tenant_id, from_number)


def _send_service_list(db: Session, tenant_id: int, to: str) -> None:
    services = db.query(Service).filter(Service.tenant_id == tenant_id).all()

    if not services:
        send_whatsapp_message(to, "Sorry, this shop hasn't set up any services yet.")
        return

    rows = [
        {
            "id": f"service:{s.id}",
            "title": s.name[:24],
            "description": f"{s.duration_minutes} min · {s.price}"[:72],
        }
        for s in services[:MAX_LIST_ROWS]
    ]

    send_whatsapp_interactive_list(
        to=to,
        header="Book an appointment",
        body="What would you like to book?",
        button_text="Choose",
        sections=[{"title": "Services", "rows": rows}],
    )

    _upsert_conversation(db, tenant_id, to, state="awaiting_service", selected_service_id=None)


def _handle_service_selected(
    db: Session,
    tenant_id: int,
    to: str,
    conversation: WhatsappConversation,
    selection_id: str,
) -> None:
    service_id = int(selection_id.split(":", 1)[1])
    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant_id)
        .first()
    )

    if not service:
        _send_service_list(db, tenant_id, to)
        return

    slots = get_available_slots(db, tenant_id, service, start_date=date.today())

    if not slots:
        send_whatsapp_message(
            to, "Sorry, there's nothing available in the next week. Please try again later."
        )
        db.delete(conversation)
        db.commit()
        return

    rows = [
        {"id": f"slot:{slot.isoformat()}", "title": slot.strftime("%a %b %d, %H:%M")}
        for slot in slots
    ]

    send_whatsapp_interactive_list(
        to=to,
        header=service.name[:60],
        body="Pick a time:",
        button_text="Choose",
        sections=[{"title": "Available times", "rows": rows}],
    )

    conversation.state = "awaiting_slot"
    conversation.selected_service_id = service.id
    db.commit()


def _handle_slot_selected(
    db: Session,
    tenant_id: int,
    to: str,
    conversation: WhatsappConversation,
    selection_id: str,
    contact_name: str | None,
) -> None:
    start_time = datetime.fromisoformat(selection_id.split(":", 1)[1])

    customer = (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == to)
        .first()
    )
    if not customer:
        customer = Customer(tenant_id=tenant_id, name=contact_name or to, phone=to)
        db.add(customer)
        db.flush()

    try:
        appointment = create_booking(
            db, tenant_id, customer.id, conversation.selected_service_id, start_time
        )
    except BookingError as err:
        if err.code == "conflict":
            send_whatsapp_message(
                to, "Sorry, that slot was just taken. Message me again to pick another time."
            )
        else:
            send_whatsapp_message(
                to, f"Sorry, something went wrong ({err.message}). Message me again to try again."
            )
        db.delete(conversation)
        db.commit()
        return

    send_whatsapp_message(
        to,
        f"You're booked for {appointment.start_time.strftime('%a %b %d at %H:%M')}. See you then!",
    )
    db.delete(conversation)
    db.commit()


def _upsert_conversation(
    db: Session,
    tenant_id: int,
    phone_number: str,
    state: str,
    selected_service_id: int | None,
) -> None:
    conversation = (
        db.query(WhatsappConversation)
        .filter(
            WhatsappConversation.tenant_id == tenant_id,
            WhatsappConversation.phone_number == phone_number,
        )
        .first()
    )

    if conversation:
        conversation.state = state
        conversation.selected_service_id = selected_service_id
    else:
        db.add(
            WhatsappConversation(
                tenant_id=tenant_id,
                phone_number=phone_number,
                state=state,
                selected_service_id=selected_service_id,
            )
        )

    db.commit()


def send_whatsapp_message(to: str, body: str) -> None:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning(
            "WhatsApp access token / phone number id not configured; "
            "skipping send to %s",
            to,
        )
        return

    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": body},
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send WhatsApp message to %s", to)


def send_whatsapp_interactive_list(
    to: str,
    header: str,
    body: str,
    button_text: str,
    sections: list[dict],
) -> None:
    if not settings.whatsapp_access_token or not settings.whatsapp_phone_number_id:
        logger.warning(
            "WhatsApp access token / phone number id not configured; "
            "skipping list send to %s",
            to,
        )
        return

    url = (
        f"https://graph.facebook.com/{WHATSAPP_API_VERSION}/"
        f"{settings.whatsapp_phone_number_id}/messages"
    )
    headers = {"Authorization": f"Bearer {settings.whatsapp_access_token}"}
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": header},
            "body": {"text": body},
            "action": {"button": button_text, "sections": sections},
        },
    }

    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
    except httpx.HTTPError:
        logger.exception("Failed to send WhatsApp interactive list to %s", to)
