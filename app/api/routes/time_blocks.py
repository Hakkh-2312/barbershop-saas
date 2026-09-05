from datetime import date as date_type
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.customer import Customer
from app.models.time_block import TimeBlock
from app.schemas.time_block import TimeBlockCreate, TimeBlockRead

router = APIRouter(
    prefix="/time-blocks",
    tags=["time-blocks"],
)


def _get_time_block_or_404(db: Session, time_block_id: int, tenant_id: int) -> TimeBlock:
    block = (
        db.query(TimeBlock)
        .filter(TimeBlock.id == time_block_id, TimeBlock.tenant_id == tenant_id)
        .first()
    )

    if not block:
        raise HTTPException(status_code=404, detail="Time block not found")

    return block


@router.post("", response_model=TimeBlockRead, status_code=201)
def create_time_block(
    payload: TimeBlockCreate,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    if payload.start_time >= payload.end_time:
        raise HTTPException(status_code=422, detail="start_time must be before end_time")

    conflict = (
        db.query(Appointment)
        .filter(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "booked",
            Appointment.start_time < payload.end_time,
            Appointment.end_time > payload.start_time,
        )
        .first()
    )

    if conflict:
        customer = db.query(Customer).filter(Customer.id == conflict.customer_id).first()
        customer_name = customer.name if customer else "a customer"
        raise HTTPException(
            status_code=409,
            detail=(
                f"You have an existing appointment with {customer_name} at "
                f"{conflict.start_time.strftime('%H:%M')} on this day - "
                "cancel or reschedule it first"
            ),
        )

    block = TimeBlock(
        tenant_id=tenant_id,
        start_time=payload.start_time,
        end_time=payload.end_time,
        reason=payload.reason,
    )
    db.add(block)
    db.commit()
    db.refresh(block)
    return block


@router.get("", response_model=list[TimeBlockRead])
def list_time_blocks(
    date: date_type | None = None,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    query = db.query(TimeBlock).filter(TimeBlock.tenant_id == tenant_id)

    if date is not None:
        day_start = datetime.combine(date, datetime.min.time())
        day_end = day_start + timedelta(days=1)
        query = query.filter(TimeBlock.start_time < day_end, TimeBlock.end_time > day_start)

    return query.order_by(TimeBlock.start_time).all()


@router.delete("/{time_block_id}", status_code=204)
def delete_time_block(
    time_block_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    block = _get_time_block_or_404(db, time_block_id, tenant_id)
    db.delete(block)
    db.commit()
