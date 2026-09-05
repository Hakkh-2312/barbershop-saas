from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AppointmentCreate(BaseModel):
    customer_id: int
    service_id: int
    start_time: datetime


class AppointmentReschedule(BaseModel):
    start_time: datetime


class AppointmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    customer_id: int
    service_id: int
    customer_name: str
    customer_phone: str
    service_name: str
    start_time: datetime
    end_time: datetime
    status: str