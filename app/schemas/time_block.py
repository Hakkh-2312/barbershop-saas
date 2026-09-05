from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimeBlockCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    reason: str | None = None


class TimeBlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    start_time: datetime
    end_time: datetime
    reason: str | None
