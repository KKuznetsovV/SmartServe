from fastapi import Depends
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_manager, require_staff
from app.db.models import User
from app.db.session import DbSession
from app.modules.printing.schemas import (
    PrinterCreate,
    PrinterOut,
    PrinterRouteCreate,
    PrinterRouteOut,
    PrinterUpdate,
    PrintJobOut,
)
from app.modules.printing.service import PrinterService

router = APIRouter()


@router.get("/locations/{location_id}/printers", response_model=list[PrinterOut])
async def list_printers(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await PrinterService(db).list_printers(location_id, current_user.business_id)


@router.get("/locations/{location_id}/print-jobs", response_model=list[PrintJobOut])
async def list_print_jobs(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await PrinterService(db).list_print_jobs(location_id, current_user.business_id)


@router.post("/printers", response_model=PrinterOut, status_code=201)
async def create_printer(
    data: PrinterCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await PrinterService(db).create_printer(data, current_user.business_id)


@router.patch("/printers/{printer_id}", response_model=PrinterOut)
async def update_printer(
    printer_id: str,
    data: PrinterUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await PrinterService(db).update_printer(printer_id, data, current_user.business_id)


@router.delete("/printers/{printer_id}", status_code=204)
async def delete_printer(
    printer_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await PrinterService(db).delete_printer(printer_id, current_user.business_id)


@router.post("/printer-routes", response_model=PrinterRouteOut, status_code=201)
async def add_printer_route(
    data: PrinterRouteCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await PrinterService(db).add_route(data, current_user.business_id)


@router.delete("/printer-routes/{route_id}", status_code=204)
async def delete_printer_route(
    route_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await PrinterService(db).delete_route(route_id, current_user.business_id)


@router.get("/locations/{location_id}/printer-routes", response_model=list[PrinterRouteOut])
async def list_printer_routes(
    location_id: str,
    db: DbSession,
    current_user: User = Depends(require_staff),
):
    return await PrinterService(db).list_routes(location_id, current_user.business_id)
