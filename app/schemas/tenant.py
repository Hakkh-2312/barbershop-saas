from pydantic import BaseModel, ConfigDict


class TenantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    phone: str | None
    address: str | None
    country_code: str | None


class TenantUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    address: str | None = None
    country_code: str | None = None
