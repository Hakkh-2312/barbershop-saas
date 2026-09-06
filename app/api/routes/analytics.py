from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service

router = APIRouter(prefix="/analytics", tags=["analytics"])

# "completed" is included for when appointments eventually get marked
# complete; "no_show" and "cancelled" never count as revenue.
REVENUE_STATUSES = ("booked", "completed")


def _resolve_range(
    range_: str, start: date_type | None, end: date_type | None
) -> tuple[datetime, datetime]:
    today = date_type.today()

    if range_ == "today":
        range_start = today
        range_end = today + timedelta(days=1)
    elif range_ == "week":
        # Sunday = start of week, matching this app's day_of_week convention
        # elsewhere (working hours, booking.py).
        days_since_sunday = (today.weekday() + 1) % 7
        range_start = today - timedelta(days=days_since_sunday)
        range_end = range_start + timedelta(days=7)
    elif range_ == "month":
        range_start = today.replace(day=1)
        if range_start.month == 12:
            range_end = range_start.replace(year=range_start.year + 1, month=1)
        else:
            range_end = range_start.replace(month=range_start.month + 1)
    elif range_ == "custom":
        if not start or not end:
            raise HTTPException(
                status_code=422, detail="start and end are required for a custom range"
            )
        if end < start:
            raise HTTPException(status_code=422, detail="end must not be before start")
        range_start = start
        range_end = end + timedelta(days=1)
    else:
        raise HTTPException(
            status_code=422, detail="range must be one of: today, week, month, custom"
        )

    return (
        datetime.combine(range_start, datetime.min.time()),
        datetime.combine(range_end, datetime.min.time()),
    )


@router.get("/overview")
def get_analytics_overview(
    range: str = Query("today"),
    start: date_type | None = None,
    end: date_type | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    range_start, range_end = _resolve_range(range, start, end)

    revenue = (
        db.query(func.coalesce(func.sum(Service.price), 0))
        .select_from(Appointment)
        .join(Service, Service.id == Appointment.service_id)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status.in_(REVENUE_STATUSES),
            Appointment.start_time >= range_start,
            Appointment.start_time < range_end,
        )
        .scalar()
    )

    new_customers = (
        db.query(Customer)
        .filter(
            Customer.tenant_id == tenant_id,
            Customer.created_at >= range_start,
            Customer.created_at < range_end,
        )
        .count()
    )

    total_customers = db.query(Customer).filter(Customer.tenant_id == tenant_id).count()

    in_range_customer_ids = [
        row[0]
        for row in db.query(Appointment.customer_id)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= range_start,
            Appointment.start_time < range_end,
        )
        .distinct()
        .all()
    ]

    returning_customers = 0
    if in_range_customer_ids:
        returning_customers = (
            db.query(Appointment.customer_id)
            .filter(
                Appointment.tenant_id == tenant_id,
                Appointment.customer_id.in_(in_range_customer_ids),
                Appointment.start_time < range_start,
            )
            .distinct()
            .count()
        )

    return {
        "range": {
            "start": range_start.date().isoformat(),
            "end": (range_end - timedelta(days=1)).date().isoformat(),
        },
        "revenue": float(revenue or 0),
        "new_customers": new_customers,
        "returning_customers": returning_customers,
        "total_customers": total_customers,
    }
