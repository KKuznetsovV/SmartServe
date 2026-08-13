"""Request schemas for the AI assistant endpoints."""

from app.schemas.base import BaseSchema


class CommandRequest(BaseSchema):
    message: str
    context: dict


class ConfirmRequest(BaseSchema):
    execution_id: str


class MenuImportMessageRequest(BaseSchema):
    session_id: str
    message: str


class MenuImportApplyRequest(BaseSchema):
    session_id: str
    items: list[dict] | None = None  # optional final edited list; falls back to the session's current items
