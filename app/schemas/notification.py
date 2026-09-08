from datetime import datetime

from pydantic import BaseModel, ConfigDict


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    message: str
    customer_name: str | None
    service_name: str | None
    appointment_time: datetime | None
    appointment_id: int | None
    is_read: bool
    created_at: datetime
