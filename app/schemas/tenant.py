from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None
    address: str | None
    country_code: str | None
    whatsapp_phone_number_id: str | None
    subscription_status: str | None
    trial_ends_at: datetime | None


class TenantUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    country_code: str | None = None
    whatsapp_phone_number_id: str | None = None
