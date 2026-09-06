from datetime import date, timedelta

import pytest

from app.core.config import settings
from app.models.appointment import Appointment


def _book(client, headers, customer_id, service_id, start_time):
    return client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": start_time},
    )


def _tomorrow_at(hour: int) -> str:
    return f"{(date.today() + timedelta(days=1)).isoformat()}T{hour:02d}:00:00"


@pytest.fixture()
def capture_sent(monkeypatch):
    monkeypatch.setattr(settings, "whatsapp_access_token", "fake-token")
    monkeypatch.setattr(settings, "whatsapp_phone_number_id", "fake-phone-id")
    monkeypatch.setattr(settings, "internal_task_secret", "test-secret")

    sent = []

    class FakeResponse:
        def raise_for_status(self):
            pass

    def fake_post(url, headers=None, json=None, timeout=None):
        sent.append(json)
        return FakeResponse()

    monkeypatch.setattr("app.services.whatsapp_client.httpx.post", fake_post)
    return sent


def test_reminder_endpoint_requires_the_secret(client):
    resp = client.post("/api/internal/send-reminders")
    assert resp.status_code == 403


def test_reminder_endpoint_rejects_wrong_secret(client, monkeypatch):
    monkeypatch.setattr(settings, "internal_task_secret", "correct-secret")
    resp = client.post(
        "/api/internal/send-reminders", headers={"X-Internal-Secret": "wrong-secret"}
    )
    assert resp.status_code == 403


def test_reminder_endpoint_accepts_header_secret(client, shop, capture_sent):
    resp = client.post(
        "/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"}
    )
    assert resp.status_code == 200


def test_reminder_endpoint_accepts_query_param_secret(client, shop, capture_sent):
    resp = client.get("/api/internal/send-reminders", params={"secret": "test-secret"})
    assert resp.status_code == 200


def test_sends_reminder_for_tomorrows_booked_appointment(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, _tomorrow_at(11))
    capture_sent.clear()  # discard the dashboard booking-confirmation send

    resp = client.post(
        "/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"}
    )
    assert resp.status_code == 200
    assert resp.json() == {"sent": 1}

    assert len(capture_sent) == 1
    assert capture_sent[0]["type"] == "template"
    assert capture_sent[0]["template"]["name"] == "appointment_reminder"
    assert capture_sent[0]["to"] == "0501234567"


def test_does_not_remind_appointments_further_out_than_tomorrow(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    far_future = (date.today() + timedelta(days=5)).isoformat()
    _book(client, headers, customer_id, service_id, f"{far_future}T11:00:00")
    capture_sent.clear()

    client.post("/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"})
    assert len(capture_sent) == 0


def test_does_not_remind_cancelled_appointments(client, shop, capture_sent):
    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, _tomorrow_at(11)).json()
    client.post(f"/api/appointments/{created['id']}/cancel", headers=headers)
    capture_sent.clear()

    client.post("/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"})
    assert len(capture_sent) == 0


def test_running_reminders_twice_does_not_double_send(client, shop, capture_sent, db_session):
    headers, customer_id, service_id = shop
    _book(client, headers, customer_id, service_id, _tomorrow_at(11))
    capture_sent.clear()

    client.post("/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"})
    client.post("/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"})

    assert len(capture_sent) == 1

    appointment = db_session.query(Appointment).first()
    assert appointment.reminder_sent is True


def test_cancel_button_cancels_the_reminded_appointment(
    client, shop, capture_sent, db_session, monkeypatch
):
    from app.core.security import decode_access_token

    headers, customer_id, service_id = shop
    created = _book(client, headers, customer_id, service_id, _tomorrow_at(11)).json()

    client.post("/api/internal/send-reminders", headers={"X-Internal-Secret": "test-secret"})

    token = headers["Authorization"].split(" ", 1)[1]
    tenant_id = decode_access_token(token)["tenant_id"]
    monkeypatch.setattr(settings, "whatsapp_tenant_id", tenant_id)

    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WABA_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {"phone_number_id": "fake-phone-id"},
                            "contacts": [{"profile": {"name": "Regular Customer"}}],
                            "messages": [
                                {
                                    "from": "0501234567",
                                    "id": "wamid.button.1",
                                    "timestamp": "1",
                                    "type": "interactive",
                                    "interactive": {
                                        "type": "button_reply",
                                        "button_reply": {
                                            "id": "CANCEL_APPOINTMENT",
                                            "title": "Cancel",
                                        },
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

    resp = client.post("/api/whatsapp/webhook", json=payload)
    assert resp.status_code == 200

    appointment = db_session.query(Appointment).filter(Appointment.id == created["id"]).first()
    assert appointment.status == "cancelled"
