from datetime import datetime

import stripe
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.core.config import settings
from app.db.session import get_db
from app.models.tenant import Tenant

# Statuses Stripe itself uses on a Subscription object - stored verbatim
# rather than remapped, so syncing is a straight copy.
_ACTIVE_STATUSES = {"trialing", "active"}


def is_billing_configured() -> bool:
    return bool(settings.stripe_secret_key and settings.stripe_price_id)


def _stripe() -> None:
    stripe.api_key = settings.stripe_secret_key


def is_subscription_active(tenant: Tenant) -> bool:
    """NULL status = grandfathered (existed before billing shipped) -
    always allowed. Otherwise: a real Stripe subscription in
    trialing/active is allowed; our own no-card trial is allowed only
    while trial_ends_at hasn't passed; anything else (past_due, canceled,
    unpaid, ...) is not."""
    if tenant.subscription_status is None:
        return True

    if tenant.subscription_status == "trialing" and not tenant.stripe_subscription_id:
        return tenant.trial_ends_at is not None and datetime.now() < tenant.trial_ends_at

    return tenant.subscription_status in _ACTIVE_STATUSES


def require_active_subscription(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
) -> None:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant or not is_subscription_active(tenant):
        raise HTTPException(
            status_code=402,
            detail="Your trial has ended. Subscribe in Settings to keep taking bookings.",
        )


def create_checkout_session(db: Session, tenant: Tenant) -> str:
    if not is_billing_configured():
        raise HTTPException(status_code=503, detail="Billing is not configured yet")

    _stripe()
    session = stripe.checkout.Session.create(
        mode="subscription",
        line_items=[{"price": settings.stripe_price_id, "quantity": 1}],
        customer=tenant.stripe_customer_id,
        client_reference_id=str(tenant.id),
        success_url=f"{settings.dashboard_url}/billing?billing=success",
        cancel_url=f"{settings.dashboard_url}/billing?billing=cancelled",
    )
    return session.url


def create_portal_session(db: Session, tenant: Tenant) -> str:
    if not is_billing_configured():
        raise HTTPException(status_code=503, detail="Billing is not configured yet")
    if not tenant.stripe_customer_id:
        raise HTTPException(status_code=404, detail="No billing account yet - subscribe first")

    _stripe()
    session = stripe.billing_portal.Session.create(
        customer=tenant.stripe_customer_id,
        return_url=f"{settings.dashboard_url}/billing",
    )
    return session.url


def handle_webhook_event(db: Session, event: dict) -> None:
    event_type = event.get("type")
    data = event.get("data", {}).get("object", {})

    if event_type == "checkout.session.completed":
        tenant_id = data.get("client_reference_id")
        if not tenant_id:
            return
        tenant = db.query(Tenant).filter(Tenant.id == int(tenant_id)).first()
        if not tenant:
            return
        tenant.stripe_customer_id = data.get("customer")
        tenant.stripe_subscription_id = data.get("subscription")
        tenant.subscription_status = "active"
        db.commit()
        return

    if event_type in ("customer.subscription.updated", "customer.subscription.deleted"):
        customer_id = data.get("customer")
        if not customer_id:
            return
        tenant = (
            db.query(Tenant).filter(Tenant.stripe_customer_id == customer_id).first()
        )
        if not tenant:
            return
        tenant.subscription_status = (
            "canceled" if event_type == "customer.subscription.deleted" else data.get("status")
        )
        db.commit()
