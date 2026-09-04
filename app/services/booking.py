from datetime import date, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.models.working_hours import WorkingHours


class BookingError(Exception):
    """Domain-level booking failure. Framework-agnostic on purpose so this
    module has no FastAPI dependency and can be called from both the REST
    routes and the WhatsApp webhook."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def check_slot_available(
    db: Session,
    tenant_id: int,
    service: Service,
    start_time: datetime,
    exclude_appointment_id: int | None = None,
) -> datetime:
    """Validates a proposed slot against working hours and existing
    bookings. Returns the computed end_time, or raises BookingError."""
    end_time = start_time + timedelta(minutes=service.duration_minutes)

    # Sunday = 0, Monday = 1, ..., Saturday = 6
    day_of_week = (start_time.weekday() + 1) % 7

    working_hours = (
        db.query(WorkingHours)
        .filter(
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week,
        )
        .first()
    )

    if not working_hours or working_hours.is_closed:
        raise BookingError("closed", "The barbershop is closed on this day")

    if (
        start_time.time() < working_hours.start_time
        or end_time.time() > working_hours.end_time
    ):
        raise BookingError("outside_hours", "Appointment is outside working hours")

    # Reject bookings that overlap an existing one for this tenant. This
    # check and the insert/update below aren't atomic on their own — two
    # concurrent requests for the same slot could both pass it before either
    # commits — so it's paired with a DB-level exclusion constraint (see the
    # Appointment model) that rejects the second write outright; callers
    # should catch IntegrityError on commit and treat it as a BookingError
    # conflict too (see create_booking below).
    conflict_query = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.status == "booked",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )

    if exclude_appointment_id is not None:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)

    if conflict_query.first():
        raise BookingError("conflict", "This time slot is no longer available")

    return end_time


def create_booking(
    db: Session,
    tenant_id: int,
    customer_id: int,
    service_id: int,
    start_time: datetime,
) -> Appointment:
    customer = (
        db.query(Customer)
        .filter(Customer.id == customer_id, Customer.tenant_id == tenant_id)
        .first()
    )
    if not customer:
        raise BookingError("not_found", "Customer not found")

    service = (
        db.query(Service)
        .filter(Service.id == service_id, Service.tenant_id == tenant_id)
        .first()
    )
    if not service:
        raise BookingError("not_found", "Service not found")

    end_time = check_slot_available(db, tenant_id, service, start_time)

    appointment = Appointment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        service_id=service.id,
        start_time=start_time,
        end_time=end_time,
        status="booked",
    )
    db.add(appointment)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise BookingError("conflict", "This time slot is no longer available")

    db.refresh(appointment)
    return appointment


def get_available_slots(
    db: Session,
    tenant_id: int,
    service: Service,
    start_date: date,
    num_days: int = 7,
    limit: int = 10,
) -> list[datetime]:
    """Available start times for `service` over `num_days` days starting at
    `start_date`, using the service's own duration as the slot step (unlike
    the fixed 20-minute step in availability.py). Returns at most `limit`
    slots, chronologically - built for WhatsApp's 10-row list cap."""
    slots: list[datetime] = []
    step = timedelta(minutes=service.duration_minutes)
    now = datetime.now()

    for day_offset in range(num_days):
        if len(slots) >= limit:
            break

        current_date = start_date + timedelta(days=day_offset)
        day_of_week = (current_date.weekday() + 1) % 7

        working_hours = (
            db.query(WorkingHours)
            .filter(
                WorkingHours.tenant_id == tenant_id,
                WorkingHours.day_of_week == day_of_week,
            )
            .first()
        )

        if not working_hours or working_hours.is_closed:
            continue

        day_start = datetime.combine(current_date, working_hours.start_time)
        day_end = datetime.combine(current_date, working_hours.end_time)

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

        current = day_start
        while current + step <= day_end:
            if current >= now and not any(
                a.start_time < current + step and a.end_time > current
                for a in appointments
            ):
                slots.append(current)
                if len(slots) >= limit:
                    break
            current += step

    return slots


def get_available_dates(
    db: Session,
    tenant_id: int,
    service: Service,
    start_date: date,
    num_days: int = 14,
) -> list[date]:
    """Which of the next `num_days` days (starting at `start_date`) have at
    least one open slot for `service`. Used for the WhatsApp date picker -
    checking one slot per day is cheap and avoids duplicating the working
    hours / overlap logic here."""
    available: list[date] = []

    for day_offset in range(num_days):
        current_date = start_date + timedelta(days=day_offset)
        if get_available_slots(db, tenant_id, service, current_date, num_days=1, limit=1):
            available.append(current_date)

    return available
