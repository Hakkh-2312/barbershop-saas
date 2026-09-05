from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.schemas.appointment import AppointmentCreate, AppointmentRead, AppointmentReschedule
from app.services.booking import BookingError, create_booking, reschedule_booking

router = APIRouter(
    prefix="/appointments",
    tags=["appointments"],
)

_STATUS_BY_ERROR_CODE = {
    "not_found": 404,
    "closed": 422,
    "outside_hours": 422,
    "blocked": 422,
    "conflict": 409,
    "not_booked": 409,
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


def _enrich_one(db: Session, appointment: Appointment) -> AppointmentRead:
    customer = db.query(Customer).filter(Customer.id == appointment.customer_id).first()
    service = db.query(Service).filter(Service.id == appointment.service_id).first()
    return AppointmentRead(
        id=appointment.id,
        customer_id=appointment.customer_id,
        service_id=appointment.service_id,
        customer_name=customer.name if customer else "",
        customer_phone=customer.phone if customer else "",
        service_name=service.name if service else "",
        start_time=appointment.start_time,
        end_time=appointment.end_time,
        status=appointment.status,
    )


def _enrich_many(db: Session, appointments: list[Appointment]) -> list[AppointmentRead]:
    customer_ids = {a.customer_id for a in appointments}
    service_ids = {a.service_id for a in appointments}

    customers = {
        c.id: c
        for c in (
            db.query(Customer).filter(Customer.id.in_(customer_ids)).all()
            if customer_ids
            else []
        )
    }
    service_names = {
        s.id: s.name
        for s in (
            db.query(Service).filter(Service.id.in_(service_ids)).all() if service_ids else []
        )
    }

    return [
        AppointmentRead(
            id=a.id,
            customer_id=a.customer_id,
            service_id=a.service_id,
            customer_name=customers[a.customer_id].name if a.customer_id in customers else "",
            customer_phone=customers[a.customer_id].phone if a.customer_id in customers else "",
            service_name=service_names.get(a.service_id, ""),
            start_time=a.start_time,
            end_time=a.end_time,
            status=a.status,
        )
        for a in appointments
    ]


@router.post("", response_model=AppointmentRead, status_code=201)
def create_appointment(
    appointment: AppointmentCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    try:
        new_appointment = create_booking(
            db,
            tenant_id,
            appointment.customer_id,
            appointment.service_id,
            appointment.start_time,
        )
    except BookingError as err:
        _raise_for_booking_error(err)

    return _enrich_one(db, new_appointment)


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

    appointments = query.order_by(Appointment.start_time).all()
    return _enrich_many(db, appointments)


@router.get("/{appointment_id}", response_model=AppointmentRead)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    appointment = _get_appointment_or_404(db, appointment_id, tenant_id)
    return _enrich_one(db, appointment)


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
    return _enrich_one(db, appointment)


@router.post("/{appointment_id}/reschedule", response_model=AppointmentRead)
def reschedule_appointment(
    appointment_id: int,
    payload: AppointmentReschedule,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    appointment = _get_appointment_or_404(db, appointment_id, tenant_id)

    try:
        appointment = reschedule_booking(db, tenant_id, appointment, payload.start_time)
    except BookingError as err:
        _raise_for_booking_error(err)

    return _enrich_one(db, appointment)
