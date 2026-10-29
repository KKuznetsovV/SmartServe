from fastapi import Depends, HTTPException, status
from smartserve_shared.routing import APIRouter

from app.api.v1.deps import require_manager
from app.db.models import User
from app.db.session import DbSession
from app.modules.catalog.discount_schemas import DiscountCreate, DiscountOut, DiscountUpdate
from app.modules.catalog.discount_service import DiscountService

router = APIRouter()


@router.post("/discounts", response_model=DiscountOut, status_code=201)
async def create_discount(
    data: DiscountCreate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    # business_id is always server-derived from the caller's own JWT, never trusted from the
    # request body — otherwise a manager could create a discount code for another business.
    data.business_id = current_user.business_id
    return await DiscountService(db).create(data)


@router.get("/businesses/{business_id}/discounts", response_model=list[DiscountOut])
async def list_discounts(
    business_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    if business_id != current_user.business_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Business not found")
    return await DiscountService(db).list_by_business(business_id)


@router.patch("/discounts/{discount_id}", response_model=DiscountOut)
async def update_discount(
    discount_id: str,
    data: DiscountUpdate,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    return await DiscountService(db).update(discount_id, data, current_user.business_id)


@router.delete("/discounts/{discount_id}", status_code=204)
async def delete_discount(
    discount_id: str,
    db: DbSession,
    current_user: User = Depends(require_manager),
):
    await DiscountService(db).delete(discount_id, current_user.business_id)
