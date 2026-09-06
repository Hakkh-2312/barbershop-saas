import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.limiter import limiter
from app.db.session import get_db
from app.services.reminders import send_due_reminders

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


def _verify_internal_secret(
    request: Request,
    x_internal_secret: str | None = Header(default=None, alias="X-Internal-Secret"),
) -> None:
    """No logged-in user exists for a scheduler ping, so this can't go
    through the normal JWT auth - a shared secret instead, accepted as
    either a header or a query param (?secret=...) since some free
    cron-ping services can't set custom headers."""
    if not settings.internal_task_secret:
        raise HTTPException(status_code=403, detail="Forbidden")

    provided = x_internal_secret or request.query_params.get("secret")
    if not provided or not hmac.compare_digest(provided, settings.internal_task_secret):
        raise HTTPException(status_code=403, detail="Forbidden")


@router.post("/send-reminders")
@router.get("/send-reminders")
@limiter.limit("10/hour")
def trigger_send_reminders(
    request: Request,
    db: Session = Depends(get_db),
    _auth: None = Depends(_verify_internal_secret),
):
    sent_count = send_due_reminders(db)
    logger.info("Sent %d appointment reminders", sent_count)
    return {"sent": sent_count}
