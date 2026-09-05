from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.time_block import TimeBlock
from app.models.working_hours import WorkingHours

router = APIRouter(
    prefix="/availability",
    tags=["availability"],
)


@router.get("")
def get_availability(
    date: date,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    # Our database uses:
    # Sunday = 0, Monday = 1, ..., Saturday = 6
    day_of_week = (date.weekday() + 1) % 7

    working_hours = (
        db.query(WorkingHours)
        .filter(
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week,
        )
        .first()
    )

    if not working_hours or working_hours.is_closed:
        return {
            "date": date,
            "slots": [],
        }

    day_start = datetime.combine(date, working_hours.start_time)
    day_end = datetime.combine(date, working_hours.end_time)

    # Get appointments for this tenant on this date.
    appointments = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time < day_end,
            Appointment.end_time > day_start,
            Appointment.status == "booked",
        )
        .all()
    )

    blocks = (
        db.query(TimeBlock)
        .filter(
            TimeBlock.tenant_id == tenant_id,
            TimeBlock.start_time < day_end,
            TimeBlock.end_time > day_start,
        )
        .all()
    )

    slots = []

    current = day_start

    while current < day_end:
        slot_end = current + timedelta(minutes=20)

        # A slot is unavailable if it overlaps an existing appointment or
        # a shop-owner time block.
        is_taken = any(
            appointment.start_time < slot_end and appointment.end_time > current
            for appointment in appointments
        ) or any(block.start_time < slot_end and block.end_time > current for block in blocks)

        if not is_taken:
            slots.append(current.strftime("%H:%M"))

        current += timedelta(minutes=20)

    return {
        "date": date,
        "slots": slots,
    }