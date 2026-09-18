from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.service import Service
from app.schemas.customer import CustomerCreate, CustomerProfile, CustomerRead, CustomerUpdate

router = APIRouter(
    prefix="/customers",
    tags=["customers"],
)

# "completed" is included for when appointments eventually get marked
# complete; "no_show" and "cancelled" never count as revenue. Mirrors
# analytics.py's REVENUE_STATUSES - keep both in sync if this changes.
_REVENUE_STATUSES = ("booked", "completed")


def _build_profile(db: Session, customer: Customer) -> CustomerProfile:
    total_appointments = (
        db.query(Appointment)
        .filter(Appointment.customer_id == customer.id, Appointment.status != "cancelled")
        .count()
    )

    total_spent = (
        db.query(func.coalesce(func.sum(Service.price), 0))
        .select_from(Appointment)
        .join(Service, Service.id == Appointment.service_id)
        .filter(
            Appointment.customer_id == customer.id,
            Appointment.status.in_(_REVENUE_STATUSES),
        )
        .scalar()
    )

    last_visit = (
        db.query(func.max(Appointment.start_time))
        .filter(
            Appointment.customer_id == customer.id,
            Appointment.status != "cancelled",
            Appointment.start_time < datetime.now(),
        )
        .scalar()
    )

    favorite = (
        db.query(Service.name)
        .select_from(Appointment)
        .join(Service, Service.id == Appointment.service_id)
        .filter(Appointment.customer_id == customer.id, Appointment.status != "cancelled")
        .group_by(Service.name)
        .order_by(func.count(Appointment.id).desc())
        .first()
    )

    return CustomerProfile(
        id=customer.id,
        name=customer.name,
        phone=customer.phone,
        email=customer.email,
        notes=customer.notes,
        total_appointments=total_appointments,
        total_spent=float(total_spent or 0),
        last_visit=last_visit,
        favorite_service=favorite[0] if favorite else None,
    )


def _get_customer_or_404(db: Session, customer_id: int, tenant_id: int) -> Customer:
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.tenant_id == tenant_id,
            Customer.is_active.is_(True),
        )
        .first()
    )

    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    return customer


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    existing = (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.phone == payload.phone)
        .first()
    )
    if existing:
        if existing.is_active:
            raise HTTPException(
                status_code=409,
                detail="A customer with this phone number already exists",
            )
        # Re-adding someone who was previously deleted - restore them with
        # the details just submitted rather than hitting the unique
        # constraint on (tenant_id, phone).
        for field, value in payload.model_dump().items():
            setattr(existing, field, value)
        existing.is_active = True
        db.commit()
        db.refresh(existing)
        return existing

    customer = Customer(tenant_id=tenant_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("", response_model=list[CustomerRead])
def list_customers(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    return (
        db.query(Customer)
        .filter(Customer.tenant_id == tenant_id, Customer.is_active.is_(True))
        .all()
    )


@router.get("/{customer_id}", response_model=CustomerProfile)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    customer = _get_customer_or_404(db, customer_id, tenant_id)
    return _build_profile(db, customer)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    customer = _get_customer_or_404(db, customer_id, tenant_id)

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(customer, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="A customer with this phone number already exists",
        )
    db.refresh(customer)
    return customer


@router.delete("/{customer_id}", status_code=204)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    customer = _get_customer_or_404(db, customer_id, tenant_id)

    has_booked_appointment = (
        db.query(Appointment)
        .filter(Appointment.customer_id == customer_id, Appointment.status == "booked")
        .first()
        is not None
    )
    if has_booked_appointment:
        raise HTTPException(
            status_code=409,
            detail="This customer has an upcoming appointment - cancel it first",
        )

    customer.is_active = False
    db.commit()
