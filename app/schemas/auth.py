from pydantic import BaseModel, Field


class SignupRequest(BaseModel):
    tenant_name: str
    email: str
    password: str = Field(min_length=8)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
