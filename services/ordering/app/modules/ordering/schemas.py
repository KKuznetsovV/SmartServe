from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator
from smartserve_shared.money import Money, OptionalMoney, Rate
from smartserve_shared.schemas import BaseSchema as BaseModel


class ApplyDiscountIn(BaseModel):
    code: str


class WsTicketIn(BaseModel):
    location_id: str


class WsTicketOut(BaseModel):
    ticket: str
    expires_in: int


class ReorderRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


class OrderItemModifierIn(BaseModel):
    """Client may send only the id; name and price come from the catalog."""

    modifier_id: str


class OrderItemModifier(BaseModel):
    modifier_id: str
    name: str
    price_delta: Money


class OrderItemOut(BaseModel):
    id: str
    order_id: str
    menu_item_id: str
    menu_item_name: str
    category_id: str | None = None
    category_name: str | None = None
    qty: int
    unit_price: Money
    modifiers: list[OrderItemModifier] = []
    notes: str | None = None
    status: str
    sort_order: int = 0
    fire_course: int = 1
    guest_number: int | None = None
    discount_type: str | None = None
    discount_value: OptionalMoney = None
    discount_amount: Money = Decimal("0.00")
    is_comped: bool = False
    comped_by: str | None = None

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    menu_item_id: str
    qty: int = Field(1, ge=1, le=99)
    modifiers: list[OrderItemModifierIn] = []
    notes: str | None = None
    fire_course: int | None = Field(None, ge=1, le=5)


class OrderItemStatusUpdate(BaseModel):
    status: str  # pending | preparing | ready | served | cancelled


class OrderItemUpdate(BaseModel):
    qty: int | None = Field(None, ge=1, le=99)
    notes: str | None = None
    modifiers: list[OrderItemModifierIn] | None = None
    fire_course: int | None = Field(None, ge=1, le=5)


class OrderOut(BaseModel):
    id: str
    location_id: str
    table_id: str | None = None
    table_name: str | None = None
    order_number: int | None = None
    business_date: date | None = None
    discount_id: str | None = None
    discount_amount: Money = Decimal("0.00")
    created_by: str | None = None
    channel: str
    status: str
    guest_count: int | None = None
    fired_courses: list[int] = []
    vat_rate: Rate = Decimal("0.18")
    subtotal: Money
    tax_amount: Money
    total: Money
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    location_id: str
    table_id: str | None = None
    channel: str = "dine_in"
    guest_count: int | None = Field(None, ge=1)
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str  # pending | confirmed | preparing | ready | paid | cancelled


class GuestAssignment(BaseModel):
    item_id: str
    guest_number: int | None = Field(None, ge=1)  # None clears the tag (item goes back to "shared")
    quantity: int | None = Field(None, ge=1)  # None = whole item; otherwise split off this many units first


class AssignGuestsRequest(BaseModel):
    assignments: list[GuestAssignment]


class ItemSelection(BaseModel):
    """One selected order item plus how many of its units the bulk action applies to.

    A `quantity` less than the item's current qty splits off a new row for just
    that many units first, leaving the remainder untouched on the original row.
    """

    item_id: str
    quantity: int | None = Field(None, ge=1)  # None = whole item


class OrderItemDiscountRequest(BaseModel):
    items: list[ItemSelection]
    discount_type: Literal["percent", "fixed"] | None = None  # both None clears the discount
    discount_value: OptionalMoney = None

    @model_validator(mode="after")
    def validate_discount_bounds(self) -> OrderItemDiscountRequest:
        if self.discount_type is None:
            return self
        if self.discount_value is None:
            raise ValueError("discountValue is required when discountType is set")
        if self.discount_type == "percent" and not (0 < self.discount_value <= 100):
            raise ValueError("Percent discount must be above 0 and at most 100")
        if self.discount_type == "fixed" and self.discount_value <= 0:
            raise ValueError("Fixed discount must be above 0")
        return self


class OrderItemCompRequest(BaseModel):
    items: list[ItemSelection]
    comped: bool


class ManagerOverride(BaseModel):
    manager_user_id: str
    pin: str
    reason: str


class OrderItemDeleteRequest(BaseModel):
    items: list[ItemSelection]
    override: ManagerOverride | None = None


class OrderFireCourseRequest(BaseModel):
    course: int = Field(..., ge=1, le=5)


class OrderWithItemsOut(OrderOut):
    items: list[OrderItemOut] = []
