import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

WHATSAPP_API_VERSION = "v21.0"


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
