from fastapi import HTTPException, status
from smartserve_shared.tenancy import verify_location_owned
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Location, MenuCategory, MenuItem, Printer, PrinterRoute, PrintJob
from app.modules.printing.schemas import PrinterCreate, PrinterRouteCreate, PrinterUpdate


class PrinterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def _owned_printer(self, printer_id: str, business_id: str) -> Printer:
        printer = await self.get_printer(printer_id)
        await verify_location_owned(self.db, printer.location_id, business_id, Location)
        return printer

    async def _item_in_business(self, item_id: str, business_id: str) -> MenuItem:
        result = await self.db.execute(
            select(MenuItem)
            .join(MenuCategory, MenuItem.category_id == MenuCategory.id)
            .join(Location, MenuCategory.location_id == Location.id)
            .where(MenuItem.id == item_id, Location.business_id == business_id)
        )
        item = result.scalar_one_or_none()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Menu item not found")
        return item

    async def list_printers(self, location_id: str, business_id: str) -> list[Printer]:
        await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(select(Printer).where(Printer.location_id == location_id))
        return list(result.scalars().all())

    async def get_printer(self, printer_id: str) -> Printer:
        result = await self.db.execute(select(Printer).where(Printer.id == printer_id))
        printer = result.scalar_one_or_none()
        if not printer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found")
        return printer

    async def create_printer(self, data: PrinterCreate, business_id: str) -> Printer:
        await verify_location_owned(self.db, data.location_id, business_id, Location)
        printer = Printer(**data.model_dump())
        self.db.add(printer)
        await self.db.flush()
        return printer

    async def update_printer(self, printer_id: str, data: PrinterUpdate, business_id: str) -> Printer:
        printer = await self._owned_printer(printer_id, business_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(printer, field, value)
        await self.db.flush()
        return printer

    async def delete_printer(self, printer_id: str, business_id: str) -> None:
        printer = await self._owned_printer(printer_id, business_id)
        await self.db.delete(printer)

    async def add_route(self, data: PrinterRouteCreate, business_id: str) -> PrinterRoute:
        printer = await self._owned_printer(data.printer_id, business_id)
        await self._item_in_business(data.item_id, business_id)
        existing = await self.db.execute(
            select(PrinterRoute).where(PrinterRoute.printer_id == printer.id, PrinterRoute.item_id == data.item_id)
        )
        route = existing.scalar_one_or_none()
        if route:
            return route
        route = PrinterRoute(printer_id=printer.id, item_id=data.item_id)
        self.db.add(route)
        await self.db.flush()
        return route

    async def delete_route(self, route_id: str, business_id: str) -> None:
        result = await self.db.execute(select(PrinterRoute).where(PrinterRoute.id == route_id))
        route = result.scalar_one_or_none()
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer route not found")
        await self._owned_printer(route.printer_id, business_id)
        await self.db.delete(route)

    async def list_routes(self, location_id: str, business_id: str) -> list[PrinterRoute]:
        await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(
            select(PrinterRoute)
            .join(Printer, PrinterRoute.printer_id == Printer.id)
            .where(Printer.location_id == location_id)
        )
        return list(result.scalars().all())

    async def list_print_jobs(self, location_id: str, business_id: str, limit: int = 100) -> list[PrintJob]:
        await verify_location_owned(self.db, location_id, business_id, Location)
        result = await self.db.execute(
            select(PrintJob)
            .join(Printer, PrintJob.printer_id == Printer.id)
            .where(Printer.location_id == location_id)
            .order_by(PrintJob.fired_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
