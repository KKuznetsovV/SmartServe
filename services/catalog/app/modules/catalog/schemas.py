from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BeforeValidator, Field, model_validator
from smartserve_shared.money import Money, OptionalMoney, OptionalRate, Rate
from smartserve_shared.schemas import BaseSchema as BaseModel


def _strip(value: object) -> object:
    if isinstance(value, str):
        return value.strip()
    return value


def _blank_to_none(value: object) -> object:
    if value is None:
        return None
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


TrimmedName = Annotated[str, BeforeValidator(_strip), Field(min_length=1, max_length=255)]
OptionalTrimmedName = Annotated[str | None, BeforeValidator(_blank_to_none), Field(min_length=1, max_length=255)]


class ModifierOut(BaseModel):
    id: str
    group_id: str
    name: str
    name_he: str | None = None
    price_delta: Money
    active: bool

    model_config = {"from_attributes": True}


class ModifierCreate(BaseModel):
    name: TrimmedName
    name_he: OptionalTrimmedName = None
    price_delta: Money = Field(default=Decimal("0.00"), ge=-1000, le=1000)


class ModifierUpdate(BaseModel):
    name: TrimmedName | None = None
    name_he: OptionalTrimmedName = None
    price_delta: OptionalMoney = Field(None, ge=-1000, le=1000)
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
    name: TrimmedName
    name_he: OptionalTrimmedName = None
    required: bool = False
    min_select: int = Field(0, ge=0)
    max_select: int = Field(1, ge=0)
    modifiers: list[ModifierCreate] = []

    @model_validator(mode="after")
    def validate_select_bounds(self) -> ModifierGroupCreate:
        validate_group_select(self.required, self.min_select, self.max_select)
        return self


class ModifierGroupUpdate(BaseModel):
    name: TrimmedName | None = None
    name_he: OptionalTrimmedName = None
    required: bool | None = None
    min_select: int | None = Field(None, ge=0)
    max_select: int | None = Field(None, ge=0)


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
    name: TrimmedName
    name_he: OptionalTrimmedName = None
    sort_order: int = Field(0, ge=0)


class MenuCategoryUpdate(BaseModel):
    parent_id: str | None = None
    name: TrimmedName | None = None
    name_he: OptionalTrimmedName = None
    sort_order: int | None = Field(None, ge=0)
    active: bool | None = None


class MenuItemOut(BaseModel):
    id: str
    category_id: str
    name: str
    name_he: str | None = None
    description: str | None = None
    description_he: str | None = None
    price: Money
    tax_rate: Rate  # deprecated: unused for totals; VAT lives on the business/location
    image_url: str | None = None
    preparation_time_min: int
    sort_order: int
    active: bool
    in_stock: bool
    default_fire_course: int = 1
    deleted_at: datetime | None = None
    modifier_groups: list[ModifierGroupOut] = []

    model_config = {"from_attributes": True}


class MenuItemCreate(BaseModel):
    category_id: str
    name: TrimmedName
    name_he: OptionalTrimmedName = None
    description: str | None = None
    description_he: str | None = None
    price: Money = Field(..., ge=0)
    tax_rate: Rate = Decimal("0.17")
    image_url: str | None = None
    preparation_time_min: int = Field(10, ge=0, le=240)
    sort_order: int | None = Field(None, ge=0)
    default_fire_course: int = 1


class MenuItemUpdate(BaseModel):
    name: TrimmedName | None = None
    name_he: OptionalTrimmedName = None
    description: str | None = None
    description_he: str | None = None
    price: OptionalMoney = Field(None, ge=0)
    tax_rate: OptionalRate = None
    image_url: str | None = None
    preparation_time_min: int | None = Field(None, ge=0, le=240)
    sort_order: int | None = Field(None, ge=0)
    active: bool | None = None
    in_stock: bool | None = None
    category_id: str | None = None
    default_fire_course: int | None = None


class BulkPriceUpdate(BaseModel):
    category_id: str | None = None  # if None, affects all items in location
    change_pct: float | None = Field(None, ge=-90, le=200)
    change_abs: float | None = None
    location_id: str

    @model_validator(mode="after")
    def exactly_one_change(self) -> BulkPriceUpdate:
        if (self.change_pct is None) == (self.change_abs is None):
            raise ValueError("Provide exactly one of changePct or changeAbs")
        return self


class StockUpdate(BaseModel):
    in_stock: bool


class ReorderRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


def validate_group_select(required: bool, min_select: int, max_select: int) -> None:
    if min_select < 0 or max_select < min_select:
        raise ValueError("minSelect must be ≥ 0 and ≤ maxSelect")
    if required and min_select < 1:
        raise ValueError("Required modifier groups need minSelect of at least 1")
