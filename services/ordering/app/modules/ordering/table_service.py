"""Table CRUD logic for the tables endpoint."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, Table
from app.modules.ordering.service import verify_location_owned
from app.modules.ordering.table_schemas import TableCreate, TableUpdate


class TableService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_tables(self, location_id: str, business_id: str | None = None) -> list[Table]:
        if business_id is not None:
            await verify_location_owned(self.db, location_id, business_id)
        result = await self.db.execute(select(Table).where(Table.location_id == location_id, Table.active))
        return list(result.scalars().all())

    async def create_table(self, data: TableCreate, business_id: str | None = None) -> Table:
        if business_id is not None:
            await verify_location_owned(self.db, data.location_id, business_id)
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
