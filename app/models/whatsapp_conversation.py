from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class WhatsappConversation(TimestampMixin, Base):
    """Tracks where a phone number is in the booking flow between webhook
    calls - WhatsApp's interactive replies carry only the tapped option's
    id, not any prior conversation context."""

    __tablename__ = "whatsapp_conversations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "phone_number", name="uq_whatsapp_conversations_tenant_phone"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    phone_number: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    state: Mapped[str] = mapped_column(String(30), nullable=False)

    selected_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
    )
