from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Tenant(TimestampMixin, Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # Digits-only country calling code (e.g. "972"), used to turn a
    # customer's locally-formatted phone number (e.g. "0501234567") into a
    # full international number for WhatsApp deep links.
    country_code: Mapped[str | None] = mapped_column(String(10), nullable=True)
    # Meta's id for this shop's connected WhatsApp Business number (from
    # the webhook payload's value.metadata.phone_number_id) - lets one
    # WhatsApp app/access token serve many shops, each with their own
    # number, instead of the single WHATSAPP_TENANT_ID env var handling
    # only one shop. Unset means this tenant isn't on WhatsApp yet.
    whatsapp_phone_number_id: Mapped[str | None] = mapped_column(
        String(50), unique=True, nullable=True
    )

    # Billing (Stripe). NULL means "grandfathered" - every tenant that
    # existed before billing shipped, exempt from subscription enforcement
    # forever. A real value ("trialing"/"active"/"past_due"/"canceled",
    # taken straight from Stripe's own subscription.status once a real
    # subscription exists) only appears once a tenant has actually gone
    # through the trial/subscribe flow.
    subscription_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    # Trials are tracked entirely on our side (no card, so no Stripe
    # subscription object exists yet) - set once at signup, checked
    # against the current time rather than relying on a webhook.
    trial_ends_at: Mapped[datetime | None] = mapped_column(nullable=True)
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
