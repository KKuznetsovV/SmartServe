from datetime import datetime

from app.schemas.base import BaseSchema as BaseModel


class OrderItemModifier(BaseModel):
    modifier_id: str
    name: str
    price_delta: float


class OrderItemOut(BaseModel):
    id: str
    order_id: str
    menu_item_id: str
    menu_item_name: str
    qty: int
    unit_price: float
    modifiers: list[OrderItemModifier] = []
    notes: str | None = None
    status: str
    sort_order: int = 0
    fire_course: int = 1
    guest_number: int | None = None
    discount_type: str | None = None
    discount_value: float | None = None
    discount_amount: float = 0.0
    is_comped: bool = False
    comped_by: str | None = None

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    menu_item_id: str
    qty: int = 1
    modifiers: list[OrderItemModifier] = []
    notes: str | None = None
    fire_course: int | None = None


class OrderItemStatusUpdate(BaseModel):
    status: str  # pending | preparing | ready | served | cancelled


class OrderItemUpdate(BaseModel):
    qty: int | None = None
    notes: str | None = None
    modifiers: list[OrderItemModifier] | None = None
    fire_course: int | None = None


class OrderOut(BaseModel):
    id: str
    location_id: str
    table_id: str | None = None
    table_name: str | None = None
    discount_id: str | None = None
    discount_amount: float = 0.0
    channel: str
    status: str
    guest_count: int | None = None
    fired_courses: list[int] = []
    subtotal: float
    tax_amount: float
    total: float
    notes: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    location_id: str
    table_id: str | None = None
    channel: str = "dine_in"
    guest_count: int | None = None
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str  # pending | confirmed | preparing | ready | paid | cancelled


class GuestAssignment(BaseModel):
    item_id: str
    guest_number: int | None = None  # None clears the tag (item goes back to "shared")
    quantity: int | None = None  # None = whole item; otherwise split off this many units first


class AssignGuestsRequest(BaseModel):
    assignments: list[GuestAssignment]


class ItemSelection(BaseModel):
    """One selected order item plus how many of its units the bulk action applies to.

    A `quantity` less than the item's current qty splits off a new row for just
    that many units first, leaving the remainder untouched on the original row.
    """

    item_id: str
    quantity: int | None = None  # None = whole item


class OrderItemDiscountRequest(BaseModel):
    items: list[ItemSelection]
    discount_type: str | None = None  # "percent" | "fixed"; both None clears the discount
    discount_value: float | None = None


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
    course: int


class OrderWithItemsOut(OrderOut):
    items: list[OrderItemOut] = []
