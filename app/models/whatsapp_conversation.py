from datetime import date

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class WhatsappConversation(TimestampMixin, Base):
    """A persistent per-(tenant, phone_number) session. Tracks where a
    customer is in the booking flow between webhook calls - WhatsApp's
    interactive replies carry only the tapped option's id, not any prior
    conversation context - and remembers their chosen language across
    visits, so it's never deleted, only reset back to "main_menu" once a
    booking completes."""

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

    language: Mapped[str] = mapped_column(String(5), nullable=False, default="ar")

    selected_service_id: Mapped[int | None] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"),
        nullable=True,
    )

    selected_date: Mapped[date | None] = mapped_column(nullable=True)

    # Set while asking "cancel or reschedule?" about an existing booking,
    # and while picking a new date/time for it in the reschedule sub-flow.
    selected_appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=True,
    )

    # Reused contextually for whichever list `state` currently points at
    # (service/date/slot) - reset to 0 whenever a new list is first shown.
    page: Mapped[int] = mapped_column(nullable=False, default=0)

    # WhatsApp's wamid of the last message actually processed from this
    # customer - Meta can and does redeliver the same webhook event (e.g.
    # if the server was slow to ack), and reprocessing an already-handled
    # tap after its state transition already happened would fall through
    # to whatever the *new* state renders instead of being a safe no-op.
    last_message_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
