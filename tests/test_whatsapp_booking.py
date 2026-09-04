import pytest

from app.core.config import settings
from app.core.security import decode_access_token
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.whatsapp_conversation import WhatsappConversation


def _tenant_id_from_headers(headers: dict) -> int:
    token = headers["Authorization"].split(" ", 1)[1]
    return decode_access_token(token)["tenant_id"]


def _text_message(from_number: str, body: str, contact_name: str = "Test Customer") -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "fake-phone-id"},
                            "contacts": [{"profile": {"name": contact_name}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": "wamid.1",
                                    "timestamp": "1",
                                    "type": "text",
                                    "text": {"body": body},
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


def _list_reply_message(
    from_number: str, reply_id: str, contact_name: str = "Test Customer"
) -> dict:
    return {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "fake-phone-id"},
                            "contacts": [{"profile": {"name": contact_name}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": "wamid.2",
                                    "timestamp": "1",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "list_reply",
                                        "list_reply": {"id": reply_id, "title": "x"},
                                    },
                                }
                            ],
                        },
                        "field": "messages",
                    }
                ],
            }
        ],
    }


@pytest.fixture()
def whatsapp_shop(client, auth_headers, monkeypatch):
    """A tenant with one service and working hours every day, wired up as
    the single WhatsApp-connected shop for the duration of the test."""
    headers = auth_headers(email="wa@shop.com", tenant_name="WA Shop")
    tenant_id = _tenant_id_from_headers(headers)

    for day in range(7):
        client.put(
            f"/api/working-hours/{day}",
            headers=headers,
            json={"start_time": "09:00:00", "end_time": "18:00:00", "is_closed": False},
        )

    service = client.post(
        "/api/services",
        headers=headers,
        json={"name": "Haircut", "duration_minutes": 20, "price": 50},
    ).json()

    monkeypatch.setattr(settings, "whatsapp_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "fake-phone-id")

    return headers, tenant_id, service["id"]


@pytest.fixture()
def capture_sent(monkeypatch):
    sent = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return FakeResponse()

    monkeypatch.setattr("app.api.routes.whatsapp.httpx.post", fake_post)
    return sent


def test_first_message_sends_service_list(client, whatsapp_shop, capture_sent):
    _headers, _tenant_id, service_id = whatsapp_shop
    phone = "15550001111"

    resp = client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    assert resp.status_code == 200

    assert len(capture_sent) == 1
    assert capture_sent[0]["type"] == "interactive"
    assert capture_sent[0]["interactive"]["type"] == "list"
    rows = capture_sent[0]["interactive"]["action"]["sections"][0]["rows"]
    assert any(r["id"] == f"service:{service_id}" for r in rows)


def test_selecting_service_sends_slot_list(client, whatsapp_shop, capture_sent, db_session):
    _headers, _tenant_id, service_id = whatsapp_shop
    phone = "15550001112"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    resp = client.post(
        "/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}")
    )
    assert resp.status_code == 200
    assert len(capture_sent) == 2

    slot_rows = capture_sent[1]["interactive"]["action"]["sections"][0]["rows"]
    assert len(slot_rows) > 0
    assert all(r["id"].startswith("slot:") for r in slot_rows)

    conversation = (
        db_session.query(WhatsappConversation)
        .filter(WhatsappConversation.phone_number == phone)
        .first()
    )
    assert conversation.state == "awaiting_slot"
    assert conversation.selected_service_id == service_id


def test_selecting_slot_books_and_autocreates_customer(
    client, whatsapp_shop, capture_sent, db_session
):
    _headers, tenant_id, service_id = whatsapp_shop
    phone = "15550001113"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}"))
    slot_rows = capture_sent[-1]["interactive"]["action"]["sections"][0]["rows"]
    chosen_slot_id = slot_rows[0]["id"]

    resp = client.post(
        "/api/whatsapp/webhook",
        json=_list_reply_message(phone, chosen_slot_id, contact_name="Jane Doe"),
    )
    assert resp.status_code == 200
    assert capture_sent[-1]["type"] == "text"
    assert "booked" in capture_sent[-1]["text"]["body"].lower()

    customer = (
        db_session.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == phone)
        .first()
    )
    assert customer is not None
    assert customer.name == "Jane Doe"

    appointment = (
        db_session.query(Appointment).filter(Appointment.customer_id == customer.id).first()
    )
    assert appointment is not None
    assert appointment.status == "booked"
    assert appointment.service_id == service_id

    conversation = (
        db_session.query(WhatsappConversation)
        .filter(WhatsappConversation.phone_number == phone)
        .first()
    )
    assert conversation is None


def test_selecting_existing_customers_phone_reuses_customer(
    client, whatsapp_shop, capture_sent, db_session
):
    headers, tenant_id, service_id = whatsapp_shop
    phone = "15550001114"

    existing = client.post(
        "/api/customers", headers=headers, json={"name": "Existing Customer", "phone": phone}
    ).json()

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}"))
    slot_rows = capture_sent[-1]["interactive"]["action"]["sections"][0]["rows"]
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, slot_rows[0]["id"]))

    appointment = (
        db_session.query(Appointment).filter(Appointment.customer_id == existing["id"]).first()
    )
    assert appointment is not None

    all_customers_for_phone = (
        db_session.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == phone)
        .all()
    )
    assert len(all_customers_for_phone) == 1


def test_conflicting_slot_selection_does_not_double_book(
    client, whatsapp_shop, capture_sent, db_session
):
    headers, tenant_id, service_id = whatsapp_shop
    phone = "15550001115"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}"))
    slot_rows = capture_sent[-1]["interactive"]["action"]["sections"][0]["rows"]
    chosen_slot_id = slot_rows[0]["id"]
    chosen_start_time = chosen_slot_id.split(":", 1)[1]

    # Someone else books that exact slot first, via the REST API.
    other_customer = client.post(
        "/api/customers", headers=headers, json={"name": "Other", "phone": "19998887777"}
    ).json()
    booked = client.post(
        "/api/appointments",
        headers=headers,
        json={
            "customer_id": other_customer["id"],
            "service_id": service_id,
            "start_time": chosen_start_time,
        },
    )
    assert booked.status_code == 201

    resp = client.post(
        "/api/whatsapp/webhook", json=_list_reply_message(phone, chosen_slot_id)
    )
    assert resp.status_code == 200
    assert "taken" in capture_sent[-1]["text"]["body"].lower()

    whatsapp_customer = (
        db_session.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == phone)
        .first()
    )
    appointments_for_whatsapp_customer = (
        db_session.query(Appointment)
        .filter(Appointment.customer_id == whatsapp_customer.id)
        .all()
        if whatsapp_customer
        else []
    )
    assert len(appointments_for_whatsapp_customer) == 0

    conversation = (
        db_session.query(WhatsappConversation)
        .filter(WhatsappConversation.phone_number == phone)
        .first()
    )
    assert conversation is None


def test_no_services_configured_sends_apology(client, auth_headers, monkeypatch, capture_sent):
    headers = auth_headers(email="empty@shop.com", tenant_name="Empty Shop")
    tenant_id = _tenant_id_from_headers(headers)
    monkeypatch.setattr(settings, "whatsapp_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "fake-phone-id")

    resp = client.post(
        "/api/whatsapp/webhook", json=_text_message("15550001116", "hi")
    )
    assert resp.status_code == 200
    assert capture_sent[0]["type"] == "text"
    assert "services" in capture_sent[0]["text"]["body"].lower()
