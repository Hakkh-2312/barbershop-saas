import itertools

import pytest

from app.core.config import settings
from app.core.security import decode_access_token

_message_id_counter = itertools.count(1)


def _tenant_id_from_headers(headers: dict) -> int:
    token = headers["Authorization"].split(" ", 1)[1]
    return decode_access_token(token)["tenant_id"]


def _text_message(
    from_number: str, body: str, phone_number_id: str, contact_name: str = "Test Customer"
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
                            "metadata": {"phone_number_id": phone_number_id},
                            "contacts": [{"profile": {"name": contact_name}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": f"wamid.{next(_message_id_counter)}",
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
    from_number: str, reply_id: str, phone_number_id: str, contact_name: str = "Test Customer"
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
                            "metadata": {"phone_number_id": phone_number_id},
                            "contacts": [{"profile": {"name": contact_name}, "wa_id": from_number}],
                            "messages": [
                                {
                                    "from": from_number,
                                    "id": f"wamid.{next(_message_id_counter)}",
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
def capture_sent(monkeypatch):
    """Same as test_whatsapp_booking's fixture, but also records the URL
    each send hit, so tests here can confirm the *correct tenant's* phone
    number id was used to send - not just that something was sent."""
    sent = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append({"url": url, "body": json})
        return FakeResponse()

    monkeypatch.setattr("app.services.whatsapp_client.httpx.post", fake_post)
    return sent


@pytest.fixture()
def two_shops(client, auth_headers, monkeypatch):
    """Two independent tenants, each with their own connected WhatsApp
    number and one service, sharing the same access token (the realistic
    "one Meta app, many shops" setup) - no legacy WHATSAPP_TENANT_ID set,
    so routing must come entirely from phone_number_id."""
    monkeypatch.setattr(settings, "whatsapp_tenant_id", None)
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", None)

    def _make_shop(email, tenant_name, phone_number_id):
        headers = auth_headers(email=email, tenant_name=tenant_name)
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

        resp = client.patch(
            "/api/tenants/me",
            headers=headers,
            json={"whatsapp_phone_number_id": phone_number_id},
        )
        assert resp.status_code == 200, resp.text

        return headers, tenant_id, service["id"]

    shop_a = _make_shop("shopa@example.com", "Shop A", "phone-id-aaa")
    shop_b = _make_shop("shopb@example.com", "Shop B", "phone-id-bbb")
    return shop_a, shop_b


def test_messages_route_to_the_tenant_owning_that_phone_number_id(
    client, two_shops, capture_sent
):
    (headers_a, tenant_a, _service_a), (headers_b, tenant_b, _service_b) = two_shops

    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002001", "hi", phone_number_id="phone-id-aaa"),
    )
    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002002", "hi", phone_number_id="phone-id-bbb"),
    )

    # Each customer registers under the tenant that owns the phone number
    # id their message came in on, not mixed up between the two shops.
    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002001", "Customer A", phone_number_id="phone-id-aaa"),
    )
    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002002", "Customer B", phone_number_id="phone-id-bbb"),
    )

    customers_a = client.get("/api/customers", headers=headers_a).json()
    customers_b = client.get("/api/customers", headers=headers_b).json()

    assert [c["name"] for c in customers_a] == ["Customer A"]
    assert [c["name"] for c in customers_b] == ["Customer B"]


def test_outbound_reply_uses_the_correct_tenants_phone_number_id(
    client, two_shops, capture_sent
):
    (headers_a, _tenant_a, _service_a), (_headers_b, _tenant_b, _service_b) = two_shops

    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002003", "hi", phone_number_id="phone-id-aaa"),
    )

    assert len(capture_sent) == 1
    assert "phone-id-aaa/messages" in capture_sent[0]["url"]


def test_second_shops_bookings_are_isolated_from_the_first(client, two_shops, capture_sent):
    (headers_a, tenant_a, service_a), (headers_b, tenant_b, service_b) = two_shops

    def _book(phone, phone_number_id, service_id):
        client.post(
            "/api/whatsapp/webhook",
            json=_text_message(phone, "hi", phone_number_id=phone_number_id),
        )
        client.post(
            "/api/whatsapp/webhook",
            json=_text_message(phone, "Repeat Customer", phone_number_id=phone_number_id),
        )
        client.post(
            "/api/whatsapp/webhook",
            json=_list_reply_message(phone, "menu:book", phone_number_id=phone_number_id),
        )
        client.post(
            "/api/whatsapp/webhook",
            json=_list_reply_message(
                phone, f"service:{service_id}", phone_number_id=phone_number_id
            ),
        )
        date_id = _rows(capture_sent[-1]["body"])[0]["id"]
        client.post(
            "/api/whatsapp/webhook",
            json=_list_reply_message(phone, date_id, phone_number_id=phone_number_id),
        )
        slot_id = _rows(capture_sent[-1]["body"])[0]["id"]
        client.post(
            "/api/whatsapp/webhook",
            json=_list_reply_message(phone, slot_id, phone_number_id=phone_number_id),
        )

    _book("15550002004", "phone-id-aaa", service_a)
    _book("15550002005", "phone-id-bbb", service_b)

    appts_a = client.get("/api/appointments", headers=headers_a).json()
    appts_b = client.get("/api/appointments", headers=headers_b).json()

    assert len(appts_a) == 1
    assert len(appts_b) == 1
    assert appts_a[0]["customer_name"] == "Repeat Customer"
    assert appts_b[0]["customer_name"] == "Repeat Customer"


def test_setting_a_phone_number_id_already_used_by_another_tenant_is_rejected(
    client, two_shops
):
    (headers_a, _tenant_a, _service_a), (headers_b, _tenant_b, _service_b) = two_shops

    resp = client.patch(
        "/api/tenants/me", headers=headers_b, json={"whatsapp_phone_number_id": "phone-id-aaa"}
    )
    assert resp.status_code == 409


def test_unrecognized_phone_number_id_falls_back_to_placeholder_reply(
    client, two_shops, capture_sent
):
    client.post(
        "/api/whatsapp/webhook",
        json=_text_message("15550002006", "hi", phone_number_id="phone-id-unknown"),
    )
    assert len(capture_sent) == 1
    assert capture_sent[0]["body"]["type"] == "text"
    assert "coming soon" in capture_sent[0]["body"]["text"]["body"]
