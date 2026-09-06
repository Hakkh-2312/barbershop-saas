from datetime import datetime, timedelta

from app.core.config import settings
from app.core.security import decode_access_token
from app.models.tenant import Tenant


def _tenant_id_from_headers(headers):
    token = headers["Authorization"].split(" ", 1)[1]
    return decode_access_token(token)["tenant_id"]


def _book(client, headers, customer_id, service_id, start_time="2026-09-10T11:00:00"):
    return client.post(
        "/api/appointments",
        headers=headers,
        json={"customer_id": customer_id, "service_id": service_id, "start_time": start_time},
    )


def test_new_signup_starts_on_an_active_trial(client, shop):
    headers, customer_id, service_id = shop
    resp = _book(client, headers, customer_id, service_id)
    assert resp.status_code == 201


def test_expired_trial_blocks_new_bookings(client, shop, db_session):
    headers, customer_id, service_id = shop
    tenant_id = _tenant_id_from_headers(headers)

    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.trial_ends_at = datetime.now() - timedelta(days=1)
    db_session.commit()

    resp = _book(client, headers, customer_id, service_id)
    assert resp.status_code == 402


def test_active_subscription_allows_bookings_past_trial(client, shop, db_session):
    headers, customer_id, service_id = shop
    tenant_id = _tenant_id_from_headers(headers)

    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.trial_ends_at = datetime.now() - timedelta(days=1)
    tenant.subscription_status = "active"
    db_session.commit()

    resp = _book(client, headers, customer_id, service_id)
    assert resp.status_code == 201


def test_canceled_subscription_blocks_bookings(client, shop, db_session):
    headers, customer_id, service_id = shop
    tenant_id = _tenant_id_from_headers(headers)

    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.subscription_status = "canceled"
    db_session.commit()

    resp = _book(client, headers, customer_id, service_id)
    assert resp.status_code == 402


def test_grandfathered_tenant_with_null_status_always_allowed(client, shop, db_session):
    """Simulates a tenant that existed before billing shipped - never had
    subscription_status touched at all."""
    headers, customer_id, service_id = shop
    tenant_id = _tenant_id_from_headers(headers)

    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.subscription_status = None
    tenant.trial_ends_at = None
    db_session.commit()

    resp = _book(client, headers, customer_id, service_id)
    assert resp.status_code == 201


def test_checkout_fails_cleanly_when_billing_unconfigured(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", None)
    monkeypatch.setattr(settings, "stripe_price_id", None)

    headers = auth_headers(tenant_name="Unconfigured Billing Shop")
    resp = client.post("/api/billing/checkout", headers=headers)
    assert resp.status_code == 503


def test_portal_requires_an_existing_stripe_customer(client, auth_headers, monkeypatch):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id", "price_fake")

    headers = auth_headers(tenant_name="No Stripe Customer Shop")
    resp = client.post("/api/billing/portal", headers=headers)
    assert resp.status_code == 404


def test_checkout_creates_a_session_and_returns_its_url(
    client, auth_headers, monkeypatch
):
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_fake")
    monkeypatch.setattr(settings, "stripe_price_id", "price_fake")

    class FakeSession:
        url = "https://checkout.stripe.com/fake-session"

    captured = {}

    def fake_create(**kwargs):
        captured.update(kwargs)
        return FakeSession()

    monkeypatch.setattr("stripe.checkout.Session.create", fake_create)

    headers = auth_headers(tenant_name="Checkout Shop")
    resp = client.post("/api/billing/checkout", headers=headers)
    assert resp.status_code == 200
    assert resp.json() == {"url": "https://checkout.stripe.com/fake-session"}
    assert captured["line_items"] == [{"price": "price_fake", "quantity": 1}]
    assert captured["client_reference_id"]


def test_webhook_rejects_missing_signature(client, monkeypatch):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")
    resp = client.post("/api/billing/webhook", json={"type": "ping"})
    assert resp.status_code == 400


def test_webhook_checkout_completed_activates_the_tenant(
    client, auth_headers, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")

    headers = auth_headers(tenant_name="Webhook Activate Shop")
    tenant_id = _tenant_id_from_headers(headers)

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "client_reference_id": str(tenant_id),
                "customer": "cus_fake123",
                "subscription": "sub_fake456",
            }
        },
    }
    monkeypatch.setattr("stripe.Webhook.construct_event", lambda *a, **k: event)

    resp = client.post(
        "/api/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=fake"}
    )
    assert resp.status_code == 200

    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    assert tenant.subscription_status == "active"
    assert tenant.stripe_customer_id == "cus_fake123"
    assert tenant.stripe_subscription_id == "sub_fake456"


def test_webhook_subscription_deleted_cancels_the_tenant(
    client, auth_headers, db_session, monkeypatch
):
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_fake")

    headers = auth_headers(tenant_name="Webhook Cancel Shop")
    tenant_id = _tenant_id_from_headers(headers)
    tenant = db_session.query(Tenant).filter(Tenant.id == tenant_id).first()
    tenant.stripe_customer_id = "cus_to_cancel"
    tenant.subscription_status = "active"
    db_session.commit()

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_to_cancel", "status": "canceled"}},
    }
    monkeypatch.setattr("stripe.Webhook.construct_event", lambda *a, **k: event)

    resp = client.post(
        "/api/billing/webhook", content=b"{}", headers={"stripe-signature": "t=1,v1=fake"}
    )
    assert resp.status_code == 200

    db_session.refresh(tenant)
    assert tenant.subscription_status == "canceled"
