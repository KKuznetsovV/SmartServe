from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Printer, PrinterRoute
from app.schemas.printer import PrinterCreate, PrinterRouteCreate, PrinterUpdate


class PrinterService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_printers(self, location_id: str) -> list[Printer]:
        result = await self.db.execute(select(Printer).where(Printer.location_id == location_id))
        return list(result.scalars().all())

    async def get_printer(self, printer_id: str) -> Printer:
        result = await self.db.execute(select(Printer).where(Printer.id == printer_id))
        printer = result.scalar_one_or_none()
        if not printer:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer not found")
        return printer

    async def create_printer(self, data: PrinterCreate) -> Printer:
        printer = Printer(**data.model_dump())
        self.db.add(printer)
        await self.db.flush()
        return printer

    async def update_printer(self, printer_id: str, data: PrinterUpdate) -> Printer:
        printer = await self.get_printer(printer_id)
        for field, value in data.model_dump(exclude_none=True).items():
            setattr(printer, field, value)
        await self.db.flush()
        return printer

    async def delete_printer(self, printer_id: str) -> None:
        printer = await self.get_printer(printer_id)
        await self.db.delete(printer)

    async def add_route(self, data: PrinterRouteCreate) -> PrinterRoute:
        existing = await self.db.execute(
            select(PrinterRoute).where(PrinterRoute.printer_id == data.printer_id, PrinterRoute.item_id == data.item_id)
        )
        route = existing.scalar_one_or_none()
        if route:
            return route
        route = PrinterRoute(printer_id=data.printer_id, item_id=data.item_id)
        self.db.add(route)
        await self.db.flush()
        return route

    async def delete_route(self, route_id: str) -> None:
        result = await self.db.execute(select(PrinterRoute).where(PrinterRoute.id == route_id))
        route = result.scalar_one_or_none()
        if not route:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Printer route not found")
        await self.db.delete(route)

    async def list_routes(self, location_id: str) -> list[PrinterRoute]:
        result = await self.db.execute(
            select(PrinterRoute)
            .join(Printer, PrinterRoute.printer_id == Printer.id)
            .where(Printer.location_id == location_id)
        )
        return list(result.scalars().all())
