from app.schemas.base import BaseSchema as BaseModel


class ModifierOut(BaseModel):
    id: str
    group_id: str
    name: str
    name_he: str | None = None
    price_delta: float
    active: bool

    model_config = {"from_attributes": True}


class ModifierCreate(BaseModel):
    name: str
    name_he: str | None = None
    price_delta: float = 0.0


class ModifierUpdate(BaseModel):
    name: str | None = None
    name_he: str | None = None
    price_delta: float | None = None
    active: bool | None = None


class ModifierGroupOut(BaseModel):
    id: str
    item_id: str
    name: str
    name_he: str | None = None
    required: bool
    min_select: int
    max_select: int
    modifiers: list[ModifierOut] = []

    model_config = {"from_attributes": True}


class ModifierGroupCreate(BaseModel):
    item_id: str
    name: str
    name_he: str | None = None
    required: bool = False
    min_select: int = 0
    max_select: int = 1
    modifiers: list[ModifierCreate] = []


class ModifierGroupUpdate(BaseModel):
    name: str | None = None
    name_he: str | None = None
    required: bool | None = None
    min_select: int | None = None
    max_select: int | None = None


class MenuCategoryOut(BaseModel):
    id: str
    location_id: str
    parent_id: str | None = None
    name: str
    name_he: str | None = None
    sort_order: int
    active: bool

    model_config = {"from_attributes": True}


class MenuCategoryCreate(BaseModel):
    location_id: str
    parent_id: str | None = None
    name: str
    name_he: str | None = None
    sort_order: int = 0


class MenuCategoryUpdate(BaseModel):
    parent_id: str | None = None
    name: str | None = None
    name_he: str | None = None
    sort_order: int | None = None
    active: bool | None = None


class MenuItemOut(BaseModel):
    id: str
    category_id: str
    name: str
    name_he: str | None = None
    description: str | None = None
    description_he: str | None = None
    price: float
    tax_rate: float
    image_url: str | None = None
    preparation_time_min: int
    active: bool
    in_stock: bool
    modifier_groups: list[ModifierGroupOut] = []

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    category_id: str
    name: str
    name_he: str | None = None
    description: str | None = None
    description_he: str | None = None
    price: float
    tax_rate: float = 0.17
    image_url: str | None = None
    preparation_time_min: int = 10


class MenuItemUpdate(BaseModel):
    name: str | None = None
    name_he: str | None = None
    description: str | None = None
    description_he: str | None = None
    price: float | None = None
    tax_rate: float | None = None
    image_url: str | None = None
    preparation_time_min: int | None = None
    active: bool | None = None
    in_stock: bool | None = None
    category_id: str | None = None


class BulkPriceUpdate(BaseModel):
    category_id: str | None = None  # if None, affects all items in location
    change_pct: float | None = None  # +10 means +10%, -5 means -5%
    change_abs: float | None = None  # absolute price delta
    location_id: str


class StockUpdate(BaseModel):
    in_stock: bool
