"""Custom APIRouter that serializes responses by alias (camelCase) by default."""

from fastapi import APIRouter as _APIRouter
from fastapi.routing import APIRoute


class _CamelRoute(APIRoute):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("response_model_by_alias", True)
        super().__init__(*args, **kwargs)


class APIRouter(_APIRouter):
    def __init__(self, *args: object, **kwargs: object) -> None:
        kwargs.setdefault("route_class", _CamelRoute)
        super().__init__(*args, **kwargs)
