from fastapi import Depends, Query
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import get_current_user, require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.ordering.table_schemas import TableCreate, TableOut, TableUpdate
from app.modules.ordering.table_service import TableService

router = APIRouter()


@router.get("/locations/{location_id}/tables", response_model=list[TableOut])
async def list_tables(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_user),
    include: str | None = Query(default=None),
):
    service = TableService(db)
    if include == "status":
        return await service.list_tables_with_status(location_id, current_user.business_id)
    tables = await service.list_tables(location_id, current_user.business_id)
    return [TableOut.model_validate(table) for table in tables]


@router.post("/tables", response_model=TableOut, status_code=201)
async def create_table(
    data: TableCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await TableService(db).create_table(data, current_user.business_id)


@router.patch("/tables/{table_id}", response_model=TableOut)
async def update_table(
    table_id: str,
    data: TableUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await TableService(db).update_table(table_id, data, current_user.business_id)


@router.delete("/tables/{table_id}", status_code=204)
async def delete_table(
    table_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await TableService(db).delete_table(table_id, current_user.business_id)
