from fastapi import HTTPException, status
from sqlalchemy import delete, select
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

    async def set_route(self, data: PrinterRouteCreate) -> PrinterRoute:
        # Remove existing route for this category if any
        await self.db.execute(delete(PrinterRoute).where(PrinterRoute.category_id == data.category_id))
        route = PrinterRoute(printer_id=data.printer_id, category_id=data.category_id)
        self.db.add(route)
        await self.db.flush()
        return route

    async def list_routes(self, location_id: str) -> list[PrinterRoute]:
        result = await self.db.execute(
            select(PrinterRoute)
            .join(Printer, PrinterRoute.printer_id == Printer.id)
            .where(Printer.location_id == location_id)
        )
        return list(result.scalars().all())
