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


def _rows(sent_payload):
    return sent_payload["interactive"]["action"]["sections"][0]["rows"]


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

    monkeypatch.setattr("app.services.whatsapp_client.httpx.post", fake_post)
    return sent


def test_first_message_sends_main_menu_in_arabic(client, whatsapp_shop, capture_sent):
    _headers, _tenant_id, _service_id = whatsapp_shop
    phone = "15550001100"

    resp = client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    assert resp.status_code == 200

    assert len(capture_sent) == 1
    assert capture_sent[0]["type"] == "interactive"
    row_ids = [r["id"] for r in _rows(capture_sent[0])]
    assert row_ids == ["menu:book", "menu:language", "menu:call", "menu:address"]
    assert "WA Shop" in capture_sent[0]["interactive"]["body"]["text"]


def test_book_option_shows_service_list(client, whatsapp_shop, capture_sent):
    _headers, _tenant_id, service_id = whatsapp_shop
    phone = "15550001101"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    resp = client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:book"))
    assert resp.status_code == 200

    rows = _rows(capture_sent[-1])
    assert any(r["id"] == f"service:{service_id}" for r in rows)
    assert "₪" in rows[0]["description"]


def test_full_booking_flow_date_then_time(client, whatsapp_shop, capture_sent, db_session):
    _headers, tenant_id, service_id = whatsapp_shop
    phone = "15550001102"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:book"))
    client.post(
        "/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}")
    )

    # First row is always a real entry - a trailing "more_x:" pagination
    # row only ever appears last, when there are more than PAGE_SIZE items
    # (every day/slot is open in this fixture, so pagination does kick in).
    date_rows = _rows(capture_sent[-1])
    assert date_rows[0]["id"].startswith("date:")
    chosen_date_id = date_rows[0]["id"]

    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, chosen_date_id))
    slot_rows = _rows(capture_sent[-1])
    assert slot_rows[0]["id"].startswith("slot:")
    chosen_slot_id = slot_rows[0]["id"]

    resp = client.post(
        "/api/whatsapp/webhook",
        json=_list_reply_message(phone, chosen_slot_id, contact_name="Jane Doe"),
    )
    assert resp.status_code == 200

    summary = capture_sent[-1]
    assert summary["type"] == "text"
    assert "✅" in summary["text"]["body"]
    assert "WA Shop" in summary["text"]["body"]

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

    # Conversation persists (for language), reset back to the main menu.
    conversation = (
        db_session.query(WhatsappConversation)
        .filter(WhatsappConversation.phone_number == phone)
        .first()
    )
    assert conversation is not None
    assert conversation.state == "main_menu"
    assert conversation.selected_service_id is None
    assert conversation.selected_date is None

    # Next message re-shows the main menu (proves the reset worked).
    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi again"))
    assert _rows(capture_sent[-1])[0]["id"] == "menu:book"


def test_language_switch_persists_across_messages(client, whatsapp_shop, capture_sent, db_session):
    _headers, _tenant_id, _service_id = whatsapp_shop
    phone = "15550001103"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:language"))
    lang_rows = _rows(capture_sent[-1])
    assert {r["id"] for r in lang_rows} == {"lang:ar", "lang:he", "lang:en"}

    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "lang:en"))
    menu_after_switch = capture_sent[-1]
    assert "Welcome to" in menu_after_switch["interactive"]["body"]["text"]

    conversation = (
        db_session.query(WhatsappConversation)
        .filter(WhatsappConversation.phone_number == phone)
        .first()
    )
    assert conversation.language == "en"

    # A brand new message later still uses English - language persisted.
    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hello again"))
    assert "Welcome to" in capture_sent[-1]["interactive"]["body"]["text"]


def test_call_option_replies_with_phone_or_fallback(
    client, whatsapp_shop, capture_sent, auth_headers
):
    headers, _tenant_id, _service_id = whatsapp_shop
    phone = "15550001104"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:call"))
    assert capture_sent[-1]["type"] == "text"
    assert "غير متوفر" in capture_sent[-1]["text"]["body"]

    client.patch("/api/tenants/me", headers=headers, json={"phone": "+972501234567"})

    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:call"))
    assert "+972501234567" in capture_sent[-1]["text"]["body"]


def test_address_option_replies_with_address_or_fallback(client, whatsapp_shop, capture_sent):
    headers, _tenant_id, _service_id = whatsapp_shop
    phone = "15550001105"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:address"))
    assert "غير متوفر" in capture_sent[-1]["text"]["body"]

    client.patch("/api/tenants/me", headers=headers, json={"address": "123 Main St"})

    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:address"))
    assert "123 Main St" in capture_sent[-1]["text"]["body"]


def test_service_list_pagination(client, whatsapp_shop, capture_sent):
    headers, _tenant_id, _service_id = whatsapp_shop
    phone = "15550001106"

    # Create enough additional services to force pagination (9 per page).
    for i in range(10):
        client.post(
            "/api/services",
            headers=headers,
            json={"name": f"Service {i}", "duration_minutes": 15, "price": 20},
        )

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:book"))

    first_page = _rows(capture_sent[-1])
    assert len(first_page) == 10
    assert first_page[-1]["id"] == "more_services:1"

    client.post(
        "/api/whatsapp/webhook", json=_list_reply_message(phone, "more_services:1")
    )
    second_page = _rows(capture_sent[-1])
    assert len(second_page) >= 1
    assert all(r["id"].startswith("service:") for r in second_page)


def test_conflicting_slot_selection_does_not_double_book(
    client, whatsapp_shop, capture_sent, db_session
):
    headers, tenant_id, service_id = whatsapp_shop
    phone = "15550001107"

    client.post("/api/whatsapp/webhook", json=_text_message(phone, "hi"))
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, "menu:book"))
    client.post(
        "/api/whatsapp/webhook", json=_list_reply_message(phone, f"service:{service_id}")
    )
    date_id = _rows(capture_sent[-1])[0]["id"]
    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, date_id))
    slot_rows = _rows(capture_sent[-1])
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

    client.post("/api/whatsapp/webhook", json=_list_reply_message(phone, chosen_slot_id))
    # The conflict reply, followed by the menu being re-offered (unlike a
    # successful booking, which ends quietly).
    assert "تم حجز" in capture_sent[-2]["text"]["body"]
    assert _rows(capture_sent[-1])[0]["id"] == "menu:book"

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


def test_no_services_configured_sends_apology(client, auth_headers, monkeypatch, capture_sent):
    headers = auth_headers(email="empty@shop.com", tenant_name="Empty Shop")
    tenant_id = _tenant_id_from_headers(headers)
    monkeypatch.setattr(settings, "whatsapp_tenant_id", tenant_id)
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "fake-phone-id")

    client.post("/api/whatsapp/webhook", json=_text_message("15550001108", "hi"))
    resp = client.post(
        "/api/whatsapp/webhook", json=_list_reply_message("15550001108", "menu:book")
    )
    assert resp.status_code == 200
    assert capture_sent[-1]["type"] == "text"
    assert "خدمات" in capture_sent[-1]["text"]["body"]
