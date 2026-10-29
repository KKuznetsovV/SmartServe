from __future__ import annotations

from smartserve_shared.routing import APIRouter
from smartserve_shared.schemas import BaseSchema


class _Item(BaseSchema):
    item_id: str


def test_base_schema_camel_case_alias() -> None:
    item = _Item(item_id="abc")
    assert item.model_dump(by_alias=True) == {"itemId": "abc"}
    parsed = _Item.model_validate({"itemId": "xyz"})
    assert parsed.item_id == "xyz"


def test_api_router_uses_camel_route() -> None:
    router = APIRouter()
    assert router.route_class.__name__ == "_CamelRoute"
