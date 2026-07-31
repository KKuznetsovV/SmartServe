from pydantic import BaseModel, EmailStr
from typing import Optional


class UserOut(BaseModel):
    id: str
    business_id: str
    email: Optional[str] = None
    name: str
    role: str
    language: str
    active: bool

    model_config = {"from_attributes": True}


class StaffCreate(BaseModel):
    email: Optional[EmailStr] = None
    name: str
    role: str = "waiter"
    language: str = "he"
    password: Optional[str] = None
    pin: Optional[str] = None


class StaffUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    language: Optional[str] = None
    active: Optional[bool] = None
    pin: Optional[str] = None
