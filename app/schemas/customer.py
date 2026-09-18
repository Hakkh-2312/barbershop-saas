from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CustomerCreate(BaseModel):
    name: str
    phone: str
    email: str | None = None


class CustomerUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None
    notes: str | None = None


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str
    email: str | None
    notes: str | None


class CustomerProfile(CustomerRead):
    """The single-customer view - CustomerRead plus stats computed from
    their appointment history, for the barber's customer profile page."""

    total_appointments: int
    total_spent: float
    last_visit: datetime | None
    favorite_service: str | None
