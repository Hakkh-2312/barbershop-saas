from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_current_tenant_id
from app.db.session import get_db
from app.models.notification import Notification
from app.schemas.notification import NotificationRead

router = APIRouter(
    prefix="/notifications",
    tags=["notifications"],
)


@router.get("", response_model=list[NotificationRead])
def list_notifications(
    unread_only: bool = False,
    limit: int = 50,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    query = db.query(Notification).filter(Notification.tenant_id == tenant_id)

    if unread_only:
        query = query.filter(Notification.is_read.is_(False))

    # created_at alone can tie (Postgres's now() returns the same value for
    # every call within one transaction), so id is a tiebreaker - it's
    # always monotonically increasing regardless.
    return (
        query.order_by(Notification.created_at.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )


@router.get("/unread-count")
def get_unread_count(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    count = (
        db.query(Notification)
        .filter(Notification.tenant_id == tenant_id, Notification.is_read.is_(False))
        .count()
    )
    return {"count": count}


@router.post("/{notification_id}/read", response_model=NotificationRead)
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.tenant_id == tenant_id)
        .first()
    )
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    db.commit()
    db.refresh(notification)
    return notification


@router.post("/read-all")
def mark_all_notifications_read(
    db: Session = Depends(get_db),
    tenant_id: int = Depends(get_current_tenant_id),
):
    (
        db.query(Notification)
        .filter(Notification.tenant_id == tenant_id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return {"status": "ok"}
