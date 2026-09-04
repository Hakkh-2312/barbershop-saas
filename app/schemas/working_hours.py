from datetime import time

from pydantic import BaseModel, ConfigDict


class WorkingHoursSet(BaseModel):
    start_time: time
    end_time: time
    is_closed: bool = False


class WorkingHoursRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    day_of_week: int
    start_time: time
    end_time: time
    is_closed: bool
