import csv
import io
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EventLog, Order, OrderItem, User
from app.modules.reports.schemas import (
    ClosedOrderOut,
    ClosedOrdersReportOut,
    ReportSummaryOut,
    SalesReportGroupOut,
    SalesReportOut,
    ServerSalesOut,
    ServerSalesReportOut,
    TopItemOut,
)

# Order statuses considered "closed" (terminal) today — see services/ordering's
# VALID_ORDER_TRANSITIONS. Kept as an explicit list (rather than "not open/submitted/...")
# so a status filter of "other" only ever matches genuinely unrecognized future statuses.
_TERMINAL_STATUSES = ("paid", "cancelled")
_ACTIVE_STATUSES = ("open", "submitted", "preparing", "ready", "served")


def _csv_row(fields: list) -> str:
    buf = io.StringIO()
    csv.writer(buf).writerow(fields)
    return buf.getvalue()


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

    async def list_events(
        self,
        business_id: str,
        routing_key: str | None = None,
        limit: int = 100,
        since: datetime | None = None,
    ) -> list[EventLog]:
        q = select(EventLog).where(EventLog.business_id == business_id)
        if routing_key:
            q = q.where(EventLog.routing_key == routing_key)
        if since is not None:
            q = q.where(EventLog.received_at >= since)
        q = q.order_by(EventLog.received_at.desc()).limit(limit)
        result = await self.db.execute(q)
        return list(result.scalars().all())

    # ─── New report types (sales by item/category/menu, sales per server, closed orders) ──

    async def sales_report(self, location_id: str, group_by: str, start: datetime, end: datetime) -> SalesReportOut:
        """Sales by item / category / whole-menu over an explicit date range.

        Only counts `paid` orders — this reports realized revenue, not open/in-flight order
        totals (same convention as `summary()`'s revenue figures).
        """
        base_filters = (
            Order.location_id == location_id,
            Order.status == "paid",
            Order.created_at >= start,
            Order.created_at <= end,
        )

        if group_by == "menu":
            totals_q = await self.db.execute(
                select(
                    func.coalesce(func.sum(OrderItem.qty), 0),
                    func.coalesce(func.sum(OrderItem.qty * OrderItem.unit_price), 0.0),
                )
                .join(Order, OrderItem.order_id == Order.id)
                .where(*base_filters)
            )
            total_qty, total_revenue = totals_q.one()
            rows = (
                [SalesReportGroupOut(group_label="Whole menu", qty=int(total_qty), revenue=float(total_revenue))]
                if total_qty
                else []
            )
            return SalesReportOut(
                group_by=group_by,
                start=start,
                end=end,
                rows=rows,
                total_qty=int(total_qty),
                total_revenue=float(total_revenue),
            )

        if group_by == "category":
            group_id_col, group_label_col = OrderItem.category_id, OrderItem.category_name
        else:  # "item"
            group_id_col, group_label_col = OrderItem.menu_item_id, OrderItem.menu_item_name

        rows_q = await self.db.execute(
            select(
                group_id_col,
                group_label_col,
                func.sum(OrderItem.qty),
                func.sum(OrderItem.qty * OrderItem.unit_price),
            )
            .join(Order, OrderItem.order_id == Order.id)
            .where(*base_filters)
            .group_by(group_id_col, group_label_col)
            .order_by(func.sum(OrderItem.qty * OrderItem.unit_price).desc())
        )
        rows = [
            SalesReportGroupOut(
                group_id=row[0],
                group_label=row[1] or "Uncategorized",
                qty=int(row[2]),
                revenue=float(row[3]),
            )
            for row in rows_q
        ]
        return SalesReportOut(
            group_by=group_by,
            start=start,
            end=end,
            rows=rows,
            total_qty=sum(r.qty for r in rows),
            total_revenue=round(sum(r.revenue for r in rows), 2),
        )

    async def sales_by_server(
        self,
        location_id: str,
        start: datetime,
        end: datetime,
        item_id: str | None = None,
        category_id: str | None = None,
    ) -> ServerSalesReportOut:
        """Sales attributed to whichever staff member created the order (`Order.created_by`).

        Without an item/category filter this reports per-server order totals (order count +
        revenue). With one, it narrows to just the qty/revenue that item or category
        contributed within each server's paid orders.
        """
        if item_id or category_id:
            q = (
                select(
                    Order.created_by,
                    User.name,
                    func.count(func.distinct(Order.id)),
                    func.sum(OrderItem.qty),
                    func.sum(OrderItem.qty * OrderItem.unit_price),
                )
                .select_from(Order)
                .join(OrderItem, OrderItem.order_id == Order.id)
                .outerjoin(User, User.id == Order.created_by)
                .where(
                    Order.location_id == location_id,
                    Order.status == "paid",
                    Order.created_at >= start,
                    Order.created_at <= end,
                )
            )
            if item_id:
                q = q.where(OrderItem.menu_item_id == item_id)
            if category_id:
                q = q.where(OrderItem.category_id == category_id)
            q = q.group_by(Order.created_by, User.name).order_by(func.sum(OrderItem.qty * OrderItem.unit_price).desc())
            result = await self.db.execute(q)
            rows = [
                ServerSalesOut(
                    server_id=row[0],
                    server_name=row[1] or "Unassigned",
                    order_count=int(row[2]),
                    qty=int(row[3] or 0),
                    revenue=float(row[4] or 0.0),
                )
                for row in result
            ]
        else:
            totals_q = (
                select(
                    Order.created_by,
                    User.name,
                    func.count(Order.id),
                    func.coalesce(func.sum(Order.total), 0.0),
                )
                .select_from(Order)
                .outerjoin(User, User.id == Order.created_by)
                .where(
                    Order.location_id == location_id,
                    Order.status == "paid",
                    Order.created_at >= start,
                    Order.created_at <= end,
                )
                .group_by(Order.created_by, User.name)
                .order_by(func.coalesce(func.sum(Order.total), 0.0).desc())
            )
            result = await self.db.execute(totals_q)
            rows = [
                ServerSalesOut(
                    server_id=row[0],
                    server_name=row[1] or "Unassigned",
                    order_count=int(row[2]),
                    revenue=float(row[3]),
                )
                for row in result
            ]

        return ServerSalesReportOut(start=start, end=end, item_id=item_id, category_id=category_id, rows=rows)

    def _closed_orders_query(self, location_id: str, start: datetime, end: datetime, status_filter: str | None):
        q = (
            select(Order, User.name)
            .select_from(Order)
            .outerjoin(User, User.id == Order.created_by)
            .where(
                Order.location_id == location_id,
                Order.created_at >= start,
                Order.created_at <= end,
            )
        )
        if status_filter == "paid":
            q = q.where(Order.status == "paid")
        elif status_filter == "cancelled":
            q = q.where(Order.status == "cancelled")
        elif status_filter == "other":
            q = q.where(Order.status.not_in((*_TERMINAL_STATUSES, *_ACTIVE_STATUSES)))
        else:
            q = q.where(Order.status.in_(_TERMINAL_STATUSES))
        return q.order_by(Order.created_at.desc())

    async def closed_orders(
        self, location_id: str, start: datetime, end: datetime, status_filter: str | None = None
    ) -> ClosedOrdersReportOut:
        """List of closed (terminal) orders over a date range, optionally narrowed to
        paid / cancelled / other (any status outside the currently-known active+terminal
        set — kept for forward compatibility; empty today since ordering only has two
        terminal statuses).
        """
        q = self._closed_orders_query(location_id, start, end, status_filter)
        result = await self.db.execute(q)
        orders = [
            ClosedOrderOut(
                id=order.id,
                status=order.status,
                channel=order.channel,
                total=order.total,
                created_by=order.created_by,
                created_by_name=name,
                created_at=order.created_at,
            )
            for order, name in result
        ]
        return ClosedOrdersReportOut(start=start, end=end, status=status_filter, orders=orders)

    # ─── CSV streaming export ──────────────────────────────────────────────────────────────

    async def stream_sales_csv(
        self, location_id: str, group_by: str, start: datetime, end: datetime
    ) -> AsyncIterator[str]:
        report = await self.sales_report(location_id, group_by, start, end)
        yield _csv_row(["group_id", "group_label", "qty", "revenue"])
        for row in report.rows:
            yield _csv_row([row.group_id or "", row.group_label, row.qty, row.revenue])

    async def stream_sales_by_server_csv(
        self,
        location_id: str,
        start: datetime,
        end: datetime,
        item_id: str | None = None,
        category_id: str | None = None,
    ) -> AsyncIterator[str]:
        report = await self.sales_by_server(location_id, start, end, item_id, category_id)
        yield _csv_row(["server_id", "server_name", "order_count", "qty", "revenue"])
        for row in report.rows:
            yield _csv_row([row.server_id or "", row.server_name, row.order_count, row.qty, row.revenue])

    async def stream_closed_orders_csv(
        self, location_id: str, start: datetime, end: datetime, status_filter: str | None = None
    ) -> AsyncIterator[str]:
        """Row-by-row CSV export using a server-side cursor (`AsyncSession.stream`, not
        `execute`) so an arbitrarily large date range's worth of closed orders never gets
        buffered into memory all at once — the only one of these reports whose result set
        can realistically be unbounded (every individual order, vs. the bounded number of
        menu items/categories/servers the other reports group by).
        """
        q = self._closed_orders_query(location_id, start, end, status_filter).execution_options(yield_per=200)
        yield _csv_row(["order_id", "status", "channel", "total", "created_by", "created_by_name", "created_at"])
        result = await self.db.stream(q)
        async for order, name in result:
            yield _csv_row(
                [
                    order.id,
                    order.status,
                    order.channel,
                    order.total,
                    order.created_by or "",
                    name or "",
                    order.created_at.isoformat(),
                ]
            )
