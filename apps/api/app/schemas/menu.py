from pydantic import BaseModel
from typing import Optional


class ModifierOut(BaseModel):
    id: str
    group_id: str
    name: str
    name_he: Optional[str] = None
    price_delta: float
    active: bool

    model_config = {"from_attributes": True}


class ModifierCreate(BaseModel):
    name: str
    name_he: Optional[str] = None
    price_delta: float = 0.0


class ModifierUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    price_delta: Optional[float] = None
    active: Optional[bool] = None


class ModifierGroupOut(BaseModel):
    id: str
    item_id: str
    name: str
    name_he: Optional[str] = None
    required: bool
    min_select: int
    max_select: int
    modifiers: list[ModifierOut] = []

    model_config = {"from_attributes": True}


class ModifierGroupCreate(BaseModel):
    item_id: str
    name: str
    name_he: Optional[str] = None
    required: bool = False
    min_select: int = 0
    max_select: int = 1
    modifiers: list[ModifierCreate] = []


class ModifierGroupUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    required: Optional[bool] = None
    min_select: Optional[int] = None
    max_select: Optional[int] = None


class MenuCategoryOut(BaseModel):
    id: str
    location_id: str
    name: str
    name_he: Optional[str] = None
    sort_order: int
    active: bool

    model_config = {"from_attributes": True}


class MenuCategoryCreate(BaseModel):
    location_id: str
    name: str
    name_he: Optional[str] = None
    sort_order: int = 0


class MenuCategoryUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    sort_order: Optional[int] = None
    active: Optional[bool] = None


class MenuItemOut(BaseModel):
    id: str
    category_id: str
    name: str
    name_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    price: float
    tax_rate: float
    image_url: Optional[str] = None
    preparation_time_min: int
    active: bool
    in_stock: bool
    modifier_groups: list[ModifierGroupOut] = []

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    category_id: str
    name: str
    name_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    price: float
    tax_rate: float = 0.17
    image_url: Optional[str] = None
    preparation_time_min: int = 10


class MenuItemUpdate(BaseModel):
    name: Optional[str] = None
    name_he: Optional[str] = None
    description: Optional[str] = None
    description_he: Optional[str] = None
    price: Optional[float] = None
    tax_rate: Optional[float] = None
    image_url: Optional[str] = None
    preparation_time_min: Optional[int] = None
    active: Optional[bool] = None
    in_stock: Optional[bool] = None
    category_id: Optional[str] = None


class BulkPriceUpdate(BaseModel):
    category_id: Optional[str] = None   # if None, affects all items in location
    change_pct: Optional[float] = None  # +10 means +10%, -5 means -5%
    change_abs: Optional[float] = None  # absolute price delta
    location_id: str
