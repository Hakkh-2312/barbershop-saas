from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.models.working_hours import WorkingHours
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentReschedule

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)


def _get_appointment_or_404(db: Session, appointment_id: int, tenant_id: int) -> Appointment:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.tenant_id == tenant_id)
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


def _check_slot_available(
    db: Session,
    tenant_id: int,
    service: Service,
    start_time: datetime,
    exclude_appointment_id: int | None = None,
) -> datetime:
    """Validates a proposed slot against working hours and existing bookings.
    Returns the computed end_time, or raises HTTPException. Shared by create
    and reschedule so they can't drift apart on the business rules."""
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
        raise HTTPException(
            status_code=422, detail="The barbershop is closed on this day"
        )

    if (
        start_time.time() < working_hours.start_time
        or end_time.time() > working_hours.end_time
    ):
        raise HTTPException(
            status_code=422, detail="Appointment is outside working hours"
        )

    # Reject bookings that overlap an existing one for this tenant. This
    # check and the insert/update below aren't atomic on their own — two
    # concurrent requests for the same slot could both pass it before either
    # commits — so it's paired with a DB-level exclusion constraint (see the
    # Appointment model) that rejects the second write outright; the
    # IntegrityError handling at each call site turns that into a clean 409
    # instead of a 500.
    conflict_query = db.query(Appointment).filter(
        Appointment.tenant_id == tenant_id,
        Appointment.status == "booked",
        Appointment.start_time < end_time,
        Appointment.end_time > start_time,
    )

    if exclude_appointment_id is not None:
        conflict_query = conflict_query.filter(Appointment.id != exclude_appointment_id)

    if conflict_query.first():
        raise HTTPException(
            status_code=409, detail="This time slot is no longer available"
        )

    return end_time


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == appointment.customer_id,
            Customer.tenant_id == tenant_id,
        )
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    service = (
        db.query(Service)
        .filter(
            Service.id == appointment.service_id,
            Service.tenant_id == tenant_id,
        )
        .first()
    )

    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    end_time = _check_slot_available(db, tenant_id, service, appointment.start_time)

    new_appointment = Appointment(
        tenant_id=tenant_id,
        customer_id=customer.id,
        service_id=service.id,
        start_time=appointment.start_time,
        end_time=end_time,
        status="booked",
    )

    db.add(new_appointment)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This time slot is no longer available"
        )

    db.refresh(new_appointment)

    return new_appointment


@router.get("", response_model=list[AppointmentRead])
def list_appointments(
    date: date_type | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    query = db.query(Appointment).filter(Appointment.tenant_id == tenant_id)

    if date is not None:
        day_start = datetime.combine(date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        query = query.filter(
            Appointment.start_time < day_end, Appointment.end_time > day_start
        )

    if status is not None:
        query = query.filter(Appointment.status == status)

    return query.order_by(Appointment.start_time).all()


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    return _get_appointment_or_404(db, appointment_id, tenant_id)


@router.post("/{appointment_id}/cancel", response_model=AppointmentRead)
def cancel_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    appointment = _get_appointment_or_404(db, appointment_id, tenant_id)

    if appointment.status != "booked":
        raise HTTPException(
            status_code=409, detail=f"Appointment is already {appointment.status}"
        )

    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)
    return appointment


@router.post("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    appointment = _get_appointment_or_404(db, appointment_id, tenant_id)

    if appointment.status != "booked":
        raise HTTPException(
            status_code=409, detail=f"Cannot reschedule a {appointment.status} appointment"
        )

    service = db.query(Service).filter(Service.id == appointment.service_id).first()

    end_time = _check_slot_available(
        db, tenant_id, service, payload.start_time, exclude_appointment_id=appointment.id
    )

    appointment.start_time = payload.start_time
    appointment.end_time = end_time

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="This time slot is no longer available"
        )

    db.refresh(appointment)
    return appointment
