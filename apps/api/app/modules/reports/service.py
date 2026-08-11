from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Order, OrderItem
from app.modules.reports.schemas import ReportSummaryOut, TopItemOut


def _period_start(period: str) -> datetime:
    now = datetime.now(UTC)
    if period == "week":
        return now - timedelta(days=7)
    if period == "month":
        return now - timedelta(days=30)
    # default: today
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


class ReportService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def summary(self, location_id: str, period: str) -> ReportSummaryOut:
        since = _period_start(period)

        # Revenue + order count from paid orders in period
        revenue_q = await self.db.execute(
            select(func.coalesce(func.sum(Order.total), 0.0), func.count(Order.id))
            .where(Order.location_id == location_id)
            .where(Order.status == "paid")
            .where(Order.created_at >= since)
        )
        total_revenue, order_count = revenue_q.one()

        avg_order_value = (total_revenue / order_count) if order_count else 0.0

        # Revenue by channel (paid orders)
        channel_q = await self.db.execute(
            select(Order.channel, func.coalesce(func.sum(Order.total), 0.0))
            .where(Order.location_id == location_id)
            .where(Order.status == "paid")
            .where(Order.created_at >= since)
            .group_by(Order.channel)
        )
        revenue_by_channel: dict[str, float] = {row[0]: row[1] for row in channel_q}

        # Order counts by status (all orders in period)
        status_q = await self.db.execute(
            select(Order.status, func.count(Order.id))
            .where(Order.location_id == location_id)
            .where(Order.created_at >= since)
            .group_by(Order.status)
        )
        orders_by_status: dict[str, int] = {row[0]: row[1] for row in status_q}

        # Top items by qty (orders in period, any status except cancelled)
        items_q = await self.db.execute(
            select(
                OrderItem.menu_item_name,
                func.sum(OrderItem.qty).label("total_qty"),
                func.sum(OrderItem.qty * OrderItem.unit_price).label("total_revenue"),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(Order.location_id == location_id)
            .where(Order.created_at >= since)
            .where(Order.status != "cancelled")
            .group_by(OrderItem.menu_item_name)
            .order_by(func.sum(OrderItem.qty).desc())
            .limit(10)
        )
        top_items = [TopItemOut(menu_item_name=row[0], qty=int(row[1]), revenue=float(row[2])) for row in items_q]

        return ReportSummaryOut(
            period=period,
            total_revenue=float(total_revenue),
            order_count=int(order_count),
            avg_order_value=round(avg_order_value, 2),
            revenue_by_channel=revenue_by_channel,
            top_items=top_items,
            orders_by_status=orders_by_status,
        )
