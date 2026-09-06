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
