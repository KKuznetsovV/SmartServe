from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_manager
from app.api.v1.router_base import APIRouter
from app.db.models import User
from app.db.session import get_db
from app.modules.catalog.discount_schemas import DiscountCreate, DiscountOut, DiscountUpdate
from app.modules.catalog.discount_service import DiscountService

router = APIRouter()


@router.post("/discounts", response_model=DiscountOut, status_code=201)
async def create_discount(
    data: DiscountCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await DiscountService(db).create(data)


@router.get("/businesses/{business_id}/discounts", response_model=list[DiscountOut])
async def list_discounts(
    business_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await DiscountService(db).list_by_business(business_id)


@router.patch("/discounts/{discount_id}", response_model=DiscountOut)
async def update_discount(
    discount_id: str,
    data: DiscountUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    return await DiscountService(db).update(discount_id, data)


@router.delete("/discounts/{discount_id}", status_code=204)
async def delete_discount(
    discount_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_manager),
):
    await DiscountService(db).delete(discount_id)
