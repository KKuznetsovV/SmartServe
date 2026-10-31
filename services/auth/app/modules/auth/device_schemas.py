from datetime import datetime
from typing import Literal

from pydantic import Field
from smartserve_shared.schemas import BaseSchema as BaseModel

DEVICE_TYPES = ("pos", "kds", "display")
DeviceType = Literal["pos", "kds", "display"]


class DeviceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    type: DeviceType = "pos"


class DeviceOut(BaseModel):
    id: str
    location_id: str
    name: str
    type: str
    created_by: str
    last_seen_at: datetime | None = None
    revoked_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class DeviceRegisterOut(DeviceOut):
    token: str
