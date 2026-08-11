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
