import pytest

from app.core.config import settings


def _book(client, headers, customer_id, service_id, start_time):
    return client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": start_time},
    )


@pytest.fixture()
def capture_sent(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "fake-phone-id")

    sent = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return FakeResponse()

    monkeypatch.setattr("app.services.whatsapp_client.httpx.post", fake_post)
    return sent


def test_dashboard_booking_notifies_the_customer(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00")

    assert len(capture_sent) == 1
    assert capture_sent[0]["to"] == "0501234567"
    assert "✅" in capture_sent[0]["text"]["body"]


def test_dashboard_cancellation_notifies_the_customer(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()
    capture_sent.clear()

    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)

    assert len(capture_sent) == 1
    # This customer was created via the dashboard, never through WhatsApp,
    # so there's no known language preference for them - the message
    # correctly defaults to the bot's default language (Arabic).
    assert "إلغاء" in capture_sent[0]["text"]["body"]


def test_dashboard_reschedule_notifies_the_customer(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00").json()
    capture_sent.clear()

    client.post(
        f"/api/appointments/{created['id']}/reschedule",
        headers=headers,
        json={"start_time": "2026-09-10T15:00:00"},
    )

    assert len(capture_sent) == 1
    assert "✅" in capture_sent[0]["text"]["body"]


def test_no_whatsapp_config_does_not_break_the_request(client, shop):
    """Without whatsapp_access_token/phone_number_id configured (the
    default in tests), the notification attempt should no-op quietly
    rather than raising - the appointment action itself must still
    succeed."""
    headers, customer_id, service_id = shop
    resp = _book(client, headers, customer_id, service_id, "2026-09-10T11:00:00")
    assert resp.status_code == 201
