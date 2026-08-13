from datetime import datetime

from app.schemas.base import BaseSchema


class TopItemOut(BaseSchema):
    menu_item_name: str
    qty: int
    revenue: float


class ReportSummaryOut(BaseSchema):
    period: str
    total_revenue: float
    order_count: int
    avg_order_value: float
    revenue_by_channel: dict[str, float]
    top_items: list[TopItemOut]
    orders_by_status: dict[str, int]


class EventLogOut(BaseSchema):
    id: str
    routing_key: str
    payload: str
    received_at: datetime

    model_config = {"from_attributes": True}
