from pydantic import EmailStr
from smartserve_shared.schemas import BaseSchema as BaseModel


class UserOut(BaseModel):
    id: str
    business_id: str
    email: str | None = None
    name: str
    role: str
    language: str
    active: bool

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    email: EmailStr | None = None
    name: str
    role: str = "waiter"
    language: str = "he"
    password: str | None = None
    pin: str | None = None


class StaffUpdate(BaseModel):
    name: str | None = None
    role: str | None = None
    language: str | None = None
    active: bool | None = None
    pin: str | None = None
