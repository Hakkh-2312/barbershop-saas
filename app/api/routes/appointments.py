from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.service import Service
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentReschedule
from app.services.booking import BookingError, check_slot_available, create_booking

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)

_STATUS_BY_ERROR_CODE = {
    "not_found": 404,
    "closed": 422,
    "outside_hours": 422,
    "conflict": 409,
}


def _raise_for_booking_error(err: BookingError):
    raise HTTPException(status_code=_STATUS_BY_ERROR_CODE[err.code], detail=err.message)


def _get_appointment_or_404(db: Session, appointment_id: int, tenant_id: int) -> Appointment:
    appointment = (
        db.query(Appointment)
        .filter(Appointment.id == appointment_id, Appointment.tenant_id == tenant_id)
        .first()
    )

    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    return appointment


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    try:
        return create_booking(
            db,
            tenant_id,
            appointment.customer_id,
            appointment.service_id,
            appointment.start_time,
        )
    except BookingError as err:
        _raise_for_booking_error(err)


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

    try:
        end_time = check_slot_available(
            db, tenant_id, service, payload.start_time, exclude_appointment_id=appointment.id
        )
    except BookingError as err:
        _raise_for_booking_error(err)

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
