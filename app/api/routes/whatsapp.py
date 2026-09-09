import hashlib
import hmac
import json
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.whatsapp_client import send_whatsapp_message
from app.services.whatsapp_flow import handle_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _has_valid_signature(body: bytes, signature_header: str | None, app_secret: str) -> bool:
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    provided = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, provided)


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
@limiter.limit("120/minute")
async def receive_message(
    request: Request, background_tasks: BackgroundTasks, db: Session = Depends(get_db)
):
    """Meta POSTs here for every event we've subscribed to (currently just
    "messages"). Routes by which WhatsApp number the message came in on
    (value.metadata.phone_number_id) so many shops can share one Meta
    app/access token, each with their own connected number; falls back to
    the legacy single-tenant WHATSAPP_TENANT_ID for a number that hasn't
    been assigned to a tenant yet.
    """
    body = await request.body()

    if settings.whatsapp_app_secret:
        signature = request.headers.get("x-hub-signature-256")
        if not _has_valid_signature(body, signature, settings.whatsapp_app_secret):
            logger.warning("Rejected WhatsApp webhook POST with invalid signature")
            raise HTTPException(status_code=403, detail="Invalid signature")
    else:
        logger.warning(
            "WHATSAPP_APP_SECRET not set - webhook signature verification is disabled"
        )

    payload = json.loads(body)

    # Meta requires a 200 within a few seconds or it retries delivery of the
    # same event - actually handling a message involves DB queries and an
    # outbound call to WhatsApp's API, which is easily slow enough to blow
    # past that window (a cold-started server especially). Acknowledge
    # immediately and do the real work after responding, so a slow reply
    # can no longer trigger Meta redelivering the same message. FastAPI
    # keeps `db` (a yield-dependency) open until background tasks finish,
    # so this is safe to reuse rather than opening a second connection.
    background_tasks.add_task(_process_webhook_payload, db, payload)
    return {"status": "ok"}


def _process_webhook_payload(db: Session, payload: dict) -> None:
    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            contact_name = _extract_contact_name(value)
            phone_number_id = value.get("metadata", {}).get("phone_number_id")
            for message in value.get("messages", []):
                try:
                    _handle_incoming(db, phone_number_id, message, contact_name)
                except Exception:
                    # One bad message shouldn't stop the rest of the
                    # payload from being processed, and there's no HTTP
                    # response left to surface this on - log it.
                    logger.exception("Failed to process incoming WhatsApp message")


def _extract_contact_name(value: dict) -> str | None:
    contacts = value.get("contacts", [])
    if contacts:
        return contacts[0].get("profile", {}).get("name")
    return None


def _resolve_tenant_id(db: Session, phone_number_id: str | None) -> int | None:
    if phone_number_id:
        tenant = (
            db.query(Tenant)
            .filter(Tenant.whatsapp_phone_number_id == phone_number_id)
            .first()
        )
        if tenant:
            return tenant.id
    # Legacy fallback: the one tenant wired up via env var, for a number
    # that hasn't been assigned to a tenant in the database yet.
    return settings.whatsapp_tenant_id


def _handle_incoming(
    db: Session, phone_number_id: str | None, message: dict, contact_name: str | None
) -> None:
    from_number = message.get("from")
    if not from_number:
        return

    tenant_id = _resolve_tenant_id(db, phone_number_id)

    if tenant_id is None:
        # No shop wired up to this WhatsApp number yet - keep the old
        # placeholder behavior rather than guessing which tenant it's for.
        text = message.get("text", {}).get("body", "")
        logger.info("WhatsApp message from %s: %r", from_number, text)
        send_whatsapp_message(
            to=from_number,
            body="Thanks for reaching out! Online booking via WhatsApp is coming soon.",
            phone_number_id=phone_number_id,
        )
        return

    handle_message(db, tenant_id, from_number, message, contact_name)
