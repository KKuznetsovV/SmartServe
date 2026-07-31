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

    model_config = {"from_attributes": True}


class OrderItemCreate(BaseModel):
    menu_item_id: str
    qty: int = 1
    modifiers: list[OrderItemModifier] = []
    notes: str | None = None


class OrderItemStatusUpdate(BaseModel):
    status: str  # pending | preparing | ready | served | cancelled


class OrderOut(BaseModel):
    id: str
    location_id: str
    table_id: str | None = None
    table_name: str | None = None
    discount_id: str | None = None
    discount_amount: float = 0.0
    channel: str
    status: str
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
    notes: str | None = None


class OrderStatusUpdate(BaseModel):
    status: str  # pending | confirmed | preparing | ready | paid | cancelled


class OrderWithItemsOut(OrderOut):
    items: list[OrderItemOut] = []
