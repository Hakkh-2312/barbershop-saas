from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Notification(TimestampMixin, Base):
    """An in-dashboard notification for the shop owner - surfaced when a
    customer does something through WhatsApp (books, cancels, reschedules)
    that the owner wouldn't otherwise know about until they happened to
    check the dashboard. Not used for actions the owner initiates
    themselves (e.g. cancelling from the dashboard) since they already
    know."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # e.g. "new_booking", "cancellation", "reschedule", "no_show" -
    # a plain string rather than an enum so new types don't need a migration.
    type: Mapped[str] = mapped_column(String(30), nullable=False)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)

    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
