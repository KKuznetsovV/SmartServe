from datetime import datetime

from smartserve_shared.money import Money
from smartserve_shared.schemas import BaseSchema


class TopItemOut(BaseSchema):
    menu_item_name: str
    qty: int
    revenue: Money


class ReportSummaryOut(BaseSchema):
    period: str
    total_revenue: Money
    order_count: int
    avg_order_value: Money
    revenue_by_channel: dict[str, Money]
    top_items: list[TopItemOut]
    orders_by_status: dict[str, int]


class EventLogOut(BaseSchema):
    id: str
    routing_key: str
    payload: str
    received_at: datetime

    model_config = {"from_attributes": True}


class SalesReportGroupOut(BaseSchema):
    group_id: str | None = None
    group_label: str
    qty: int
    revenue: Money


class SalesReportOut(BaseSchema):
    group_by: str  # "item" | "category" | "menu"
    start: datetime
    end: datetime
    rows: list[SalesReportGroupOut]
    total_qty: int
    total_revenue: Money


class ServerSalesOut(BaseSchema):
    server_id: str | None = None
    server_name: str
    order_count: int
    qty: int | None = None  # only meaningful when filtered by item_id/category_id
    revenue: Money


class ServerSalesReportOut(BaseSchema):
    start: datetime
    end: datetime
    item_id: str | None = None
    category_id: str | None = None
    rows: list[ServerSalesOut]


class ClosedOrderOut(BaseSchema):
    id: str
    status: str
    channel: str
    total: Money
    created_by: str | None = None
    created_by_name: str | None = None
    created_at: datetime


class ClosedOrdersReportOut(BaseSchema):
    start: datetime
    end: datetime
    status: str | None = None
    orders: list[ClosedOrderOut]
