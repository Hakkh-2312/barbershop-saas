from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
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

    # English fallback text - always stored so the dashboard has something
    # to show for older rows created before customer_name/service_name/
    # appointment_time existed, or for a type the frontend doesn't know how
    # to localize. Kept in sync with those fields for every new row.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(String(1000), nullable=False)

    # Snapshotted at creation time (not a live join to the appointment) so
    # the notification keeps describing what actually happened even if the
    # appointment is later changed again - lets the dashboard render this
    # in the shop owner's current language instead of being stuck in
    # whatever English sentence was baked in above.
    customer_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    service_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    appointment_time: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)

    appointment_id: Mapped[int | None] = mapped_column(
        ForeignKey("appointments.id", ondelete="CASCADE"),
        nullable=True,
    )

    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
