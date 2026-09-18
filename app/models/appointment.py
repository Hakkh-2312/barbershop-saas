from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ExcludeConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Appointment(TimestampMixin, Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    customer_id: Mapped[int] = mapped_column(
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    start_time: Mapped[datetime] = mapped_column(
        nullable=False,
        index=True,
    )

    end_time: Mapped[datetime] = mapped_column(
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="booked",
    )

    # Guards against sending a customer the same day-before reminder
    # twice (e.g. if the daily job is retried or accidentally runs again).
    reminder_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # Set when the customer taps "I'll be there" on their reminder. Reset
    # to False on reschedule (see booking.py) - a confirmation is only
    # meaningful for the specific time it was given for.
    confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('booked', 'cancelled', 'completed', 'no_show')",
            name="ck_appointments_status",
        ),
        # Belt-and-braces against the double-booking race the app-level
        # overlap check in appointments.py can't fully close on its own:
        # two concurrent requests for the same slot both pass that check
        # before either commits. This constraint makes Postgres itself
        # reject the second insert. Requires the btree_gist extension
        # (enabled in the migration) for the integer equality operator
        # class used alongside the range overlap operator.
        ExcludeConstraint(
            (tenant_id, "="),
            (func.tsrange(start_time, end_time), "&&"),
            where=(status == "booked"),
            using="gist",
            name="no_overlapping_bookings",
        ),
    )
