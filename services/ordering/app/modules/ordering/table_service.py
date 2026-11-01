"""Table CRUD logic for the tables endpoint."""

from fastapi import HTTPException, status
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, Order, Table
from app.modules.ordering.table_schemas import TableCreate, TableOpenOrderOut, TableOut, TableUpdate

OPEN_FLOOR_STATUSES = ("open", "submitted", "preparing", "ready", "served", "split")


def floor_state_for_order(status: str | None) -> str:
    if status is None:
        return "free"
    if status == "open":
        return "seated"
    if status in ("submitted", "preparing"):
        return "ordered"
    if status == "ready":
        return "food_ready"
    if status in ("served", "split"):
        return "waiting_to_pay"
    return "seated"


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tables(self, location_id: str, business_id: str | None = None) -> list[Table]:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(select(Table).where(Table.location_id == location_id, Table.active))
        return list(result.scalars().all())

    async def list_tables_with_status(self, location_id: str, business_id: str | None = None) -> list[TableOut]:
        tables = await self.list_tables(location_id, business_id)
        if not tables:
            return []
        result = await self.db.execute(
            select(Order)
            .where(
                Order.location_id == location_id,
                Order.table_id.in_([t.id for t in tables]),
                Order.status.in_(OPEN_FLOOR_STATUSES),
            )
            .order_by(Order.created_at.desc())
        )
        latest: dict[str, Order] = {}
        for order in result.scalars().all():
            if order.table_id and order.table_id not in latest:
                latest[order.table_id] = order
        out: list[TableOut] = []
        for table in tables:
            payload = TableOut.model_validate(table)
            order = latest.get(table.id)
            if order is None:
                out.append(payload)
                continue
            out.append(
                payload.model_copy(
                    update={
                        "floor_state": floor_state_for_order(order.status),
                        "open_order": TableOpenOrderOut(
                            id=order.id,
                            status=order.status,
                            guest_count=order.guest_count,
                            seated_since=order.created_at,
                            total=order.total,
                        ),
                    }
                )
            )
        return out

    async def create_table(self, data: TableCreate, business_id: str | None = None) -> Table:
        if business_id is not None:
            await verify_location_owned(self.db, data.location_id, business_id, Location)
        table = Table(**data.model_dump())
        self.db.add(table)
        await self.db.flush()
        return table

    async def get_table(self, table_id: str, business_id: str | None = None) -> Table:
        q = select(Table).where(Table.id == table_id)
        if business_id is not None:
            q = q.join(Location, Table.location_id == Location.id).where(Location.business_id == business_id)
        result = await self.db.execute(q)
        table = result.scalar_one_or_none()
        if not table:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
        return table

    async def update_table(self, table_id: str, data: TableUpdate, business_id: str | None = None) -> Table:
        table = await self.get_table(table_id, business_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(table, field, value)
        await self.db.flush()
        return table

    async def delete_table(self, table_id: str, business_id: str | None = None) -> None:
        table = await self.get_table(table_id, business_id)
        await self.db.delete(table)
