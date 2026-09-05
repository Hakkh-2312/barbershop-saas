import hashlib
import hmac
import json


def test_webhook_verification_succeeds_with_correct_token(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_verify_token", "secret-token")

    resp = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "secret-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 200
    assert resp.text == "12345"


def test_webhook_verification_fails_with_wrong_token(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_verify_token", "secret-token")

    resp = client.get(
        "/api/whatsapp/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "wrong-token",
            "hub.challenge": "12345",
        },
    )
    assert resp.status_code == 403


def test_webhook_verification_missing_params_rejected(client):
    resp = client.get("/api/whatsapp/webhook")
    assert resp.status_code == 422


def test_incoming_message_webhook_accepted(client, monkeypatch):
    # Explicitly force the "no shop wired up yet" fallback path, regardless
    # of whatever WHATSAPP_TENANT_ID happens to be set to in the local .env
    # this test suite is run against.
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_tenant_id", None)

    # Realistic shape of a Meta WhatsApp Cloud API "messages" webhook event.
    # No WHATSAPP_ACCESS_TOKEN/PHONE_NUMBER_ID configured in tests, so the
    # reply-send is skipped without making a real network call - this test
    # only checks the inbound side is parsed without error.
    payload = {
        "object": "whatsapp_business_account",
        "entry": [
            {
                "id": "WHATSAPP_BUSINESS_ACCOUNT_ID",
                "changes": [
                    {
                        "value": {
                            "messaging_product": "whatsapp",
                            "metadata": {
                                "display_phone_number": "16505551111",
                                "phone_number_id": "123456123",
                            },
                            "contacts": [
                                {"profile": {"name": "Test User"}, "wa_id": "16505552222"}
                            ],
                            "messages": [
                                {
                                    "from": "16505552222",
                                    "id": "wamid.ID",
                                    "timestamp": "1234567890",
                                    "text": {"body": "Hi, I'd like a haircut"},
                                    "type": "text",
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
    assert resp.json() == {"status": "ok"}


def test_webhook_handles_non_message_events_gracefully(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_tenant_id", None)
    # e.g. a delivery-status callback, which has no "messages" key.
    payload = {
        "object": "whatsapp_business_account",
        "entry": [{"id": "x", "changes": [{"value": {"statuses": []}, "field": "messages"}]}],
    }
    resp = client.post("/api/whatsapp/webhook", json=payload)
    assert resp.status_code == 200


def test_webhook_rejects_missing_signature_when_app_secret_configured(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_app_secret", "shh")
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_tenant_id", None)

    payload = {"object": "whatsapp_business_account", "entry": []}
    resp = client.post("/api/whatsapp/webhook", json=payload)
    assert resp.status_code == 403


def test_webhook_rejects_wrong_signature_when_app_secret_configured(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_app_secret", "shh")
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_tenant_id", None)

    body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
    resp = client.post(
        "/api/whatsapp/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": "sha256=" + "0" * 64,
        },
    )
    assert resp.status_code == 403


def test_webhook_accepts_valid_signature_when_app_secret_configured(client, monkeypatch):
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_app_secret", "shh")
    monkeypatch.setattr("app.api.routes.whatsapp.settings.whatsapp_tenant_id", None)

    body = json.dumps({"object": "whatsapp_business_account", "entry": []}).encode()
    signature = hmac.new(b"shh", body, hashlib.sha256).hexdigest()
    resp = client.post(
        "/api/whatsapp/webhook",
        content=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Signature-256": f"sha256={signature}",
        },
    )
    assert resp.status_code == 200
