from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.db.models import Table, User
from app.schemas.table import TableOut, TableCreate, TableUpdate
from app.api.v1.deps import get_current_user, require_manager

router = APIRouter()


@router.get("/locations/{location_id}/tables", response_model=list[TableOut])
async def list_tables(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(get_current_user),
):
    result = await db.execute(select(Table).where(Table.location_id == location_id, Table.active == True))
    return result.scalars().all()


@router.post("/tables", response_model=TableOut, status_code=201)
async def create_table(
    data: TableCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    table = Table(**data.model_dump())
    db.add(table)
    await db.flush()
    return table


@router.patch("/tables/{table_id}", response_model=TableOut)
async def update_table(
    table_id: str,
    data: TableUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    from fastapi import HTTPException, status
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(table, field, value)
    return table


@router.delete("/tables/{table_id}", status_code=204)
async def delete_table(
    table_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    from fastapi import HTTPException, status
    result = await db.execute(select(Table).where(Table.id == table_id))
    table = result.scalar_one_or_none()
    if not table:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Table not found")
    await db.delete(table)
