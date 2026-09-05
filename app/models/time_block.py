from datetime import datetime

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class TimeBlock(TimestampMixin, Base):
    """A shop-owner-imposed period of unavailability (e.g. a personal
    appointment) - distinct from a customer Appointment. One-off only (a
    specific date/time range), not recurring."""

    __tablename__ = "time_blocks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(nullable=False, index=True)
    end_time: Mapped[datetime] = mapped_column(nullable=False)

    reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
