from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.working_hours import WorkingHours
from app.schemas.working_hours import WorkingHoursRead, WorkingHoursSet

router = APIRouter(
    prefix="/working-hours",
    tags=["working-hours"],
)


@router.get("", response_model=list[WorkingHoursRead])
def list_working_hours(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    return (
        db.query(WorkingHours)
        .filter(WorkingHours.tenant_id == tenant_id)
        .order_by(WorkingHours.day_of_week)
        .all()
    )


@router.put("/{day_of_week}", response_model=WorkingHoursRead)
def set_working_hours(
    payload: WorkingHoursSet,
    day_of_week: int = Path(ge=0, le=6),
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    working_hours = (
        db.query(WorkingHours)
        .filter(
            WorkingHours.tenant_id == tenant_id,
            WorkingHours.day_of_week == day_of_week,
        )
        .first()
    )

    if working_hours:
        working_hours.start_time = payload.start_time
        working_hours.end_time = payload.end_time
        working_hours.is_closed = payload.is_closed
    else:
        working_hours = WorkingHours(
            tenant_id=tenant_id,
            day_of_week=day_of_week,
            **payload.model_dump(),
        )
        db.add(working_hours)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Working hours for this day were just modified elsewhere, retry",
        )

    db.refresh(working_hours)
    return working_hours
