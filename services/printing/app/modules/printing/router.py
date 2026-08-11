from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.modules.printing.schemas import PrinterCreate, PrinterOut, PrinterRouteCreate, PrinterRouteOut, PrinterUpdate
from app.modules.printing.service import PrinterService

router = APIRouter()


@router.get("/locations/{location_id}/printers", response_model=list[PrinterOut])
async def list_printers(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await PrinterService(db).list_printers(location_id)


@router.post("/printers", response_model=PrinterOut, status_code=201)
async def create_printer(
    data: PrinterCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await PrinterService(db).create_printer(data)


@router.patch("/printers/{printer_id}", response_model=PrinterOut)
async def update_printer(
    printer_id: str,
    data: PrinterUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await PrinterService(db).update_printer(printer_id, data)


@router.delete("/printers/{printer_id}", status_code=204)
async def delete_printer(
    printer_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await PrinterService(db).delete_printer(printer_id)


@router.post("/printer-routes", response_model=PrinterRouteOut, status_code=201)
async def add_printer_route(
    data: PrinterRouteCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await PrinterService(db).add_route(data)


@router.delete("/printer-routes/{route_id}", status_code=204)
async def delete_printer_route(
    route_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await PrinterService(db).delete_route(route_id)


@router.get("/locations/{location_id}/printer-routes", response_model=list[PrinterRouteOut])
async def list_printer_routes(
    location_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await PrinterService(db).list_routes(location_id)
