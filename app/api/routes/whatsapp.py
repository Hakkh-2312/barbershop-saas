import logging

import httpx
from fastapi import APIRouter, HTTPException, Query, Request, Response

from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])

WHATSAPP_API_VERSION = "v21.0"


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
async def receive_message(request: Request):
    """Meta POSTs here for every event we've subscribed to (currently just
    "messages"). No per-tenant routing yet - this handles a single shop's
    WhatsApp number; mapping incoming numbers to tenants is future work
    once more than one real shop is on WhatsApp.
    """
    payload = await request.json()

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            for message in change.get("value", {}).get("messages", []):
                from_number = message.get("from")
                text = message.get("text", {}).get("body", "")
                logger.info("WhatsApp message from %s: %r", from_number, text)

                if from_number:
                    send_whatsapp_message(
                        to=from_number,
                        body=(
                            "Thanks for reaching out! Online booking via "
                            "WhatsApp is coming soon."
                        ),
                    )

    # Meta requires a 200 within a few seconds regardless of what we did
    # with the payload, or it will retry (and eventually disable) delivery.
    return {"status": "ok"}


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
