import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.services.whatsapp_client import send_whatsapp_message
from app.services.whatsapp_flow import handle_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


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
                _handle_incoming(db, message, contact_name)

    # Meta requires a 200 within a few seconds regardless of what we did
    # with the payload, or it will retry (and eventually disable) delivery.
    return {"status": "ok"}


def _extract_contact_name(value: dict) -> str | None:
    contacts = value.get("contacts", [])
    if contacts:
        return contacts[0].get("profile", {}).get("name")
    return None


def _handle_incoming(db: Session, message: dict, contact_name: str | None) -> None:
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

    handle_message(db, settings.whatsapp_tenant_id, from_number, message, contact_name)
