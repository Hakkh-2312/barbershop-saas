from datetime import time

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class WorkingHours(TimestampMixin, Base):
    __tablename__ = "working_hours"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "day_of_week", name="uq_working_hours_tenant_day"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    day_of_week: Mapped[int] = mapped_column(nullable=False)

    start_time: Mapped[time] = mapped_column(nullable=False)

    end_time: Mapped[time] = mapped_column(nullable=False)

    is_closed: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
