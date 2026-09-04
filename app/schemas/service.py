from pydantic import BaseModel, ConfigDict, Field


class ServiceCreate(BaseModel):
    name: str
    duration_minutes: int = Field(gt=0)
    price: int = Field(gt=0)


class ServiceUpdate(BaseModel):
    name: str | None = None
    duration_minutes: int | None = Field(default=None, gt=0)
    price: int | None = Field(default=None, gt=0)


class ServiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    duration_minutes: int
    price: int
