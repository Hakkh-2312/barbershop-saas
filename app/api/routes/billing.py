import logging

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.models.tenant import Tenant
from app.services.billing import (
    create_checkout_session,
    create_portal_session,
    handle_webhook_event,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["billing"])


def _get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return tenant


@router.post("/checkout")
def start_checkout(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    tenant = _get_tenant_or_404(db, tenant_id)
    return {"url": create_checkout_session(db, tenant)}


@router.post("/portal")
def open_billing_portal(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    tenant = _get_tenant_or_404(db, tenant_id)
    return {"url": create_portal_session(db, tenant)}


@router.post("/webhook")
@limiter.limit("60/minute")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    if not settings.stripe_webhook_secret:
        logger.warning("STRIPE_WEBHOOK_SECRET not set - rejecting Stripe webhook")
        raise HTTPException(status_code=503, detail="Billing webhook not configured")

    body = await request.body()
    signature = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            body, signature, settings.stripe_webhook_secret
        )
    except (ValueError, stripe.SignatureVerificationError):
        logger.warning("Rejected Stripe webhook with invalid signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    handle_webhook_event(db, event)
    return {"status": "ok"}
