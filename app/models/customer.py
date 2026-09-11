from sqlalchemy import Boolean, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import TimestampMixin


class Customer(TimestampMixin, Base):
    __tablename__ = "customers"
    __table_args__ = (
        UniqueConstraint("tenant_id", "phone", name="uq_customers_tenant_phone"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    tenant_id: Mapped[int] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    phone: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # "Deleting" a customer archives them instead of removing the row -
    # appointments.customer_id is ON DELETE RESTRICT (cancelled or not, the
    # row stays for history/analytics), so a real delete would always fail
    # for any customer who ever booked. Archived customers are hidden from
    # the dashboard list but keep their appointment history intact.
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
