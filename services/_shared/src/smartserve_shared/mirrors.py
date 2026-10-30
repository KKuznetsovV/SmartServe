"""Read-only ORM mirrors of tables owned by another service."""

from __future__ import annotations

import os

from sqlalchemy import event
from sqlalchemy.orm import Session


class ReadOnlyMirrorError(RuntimeError):
    """Raised when a service tries to persist a table it does not own."""


class ReadOnlyMirror:
    """Mixin for mapped classes that must not be inserted, updated, or deleted."""


def _mirror_writes_allowed(session: Session) -> bool:
    if session.info.get("allow_mirror_writes"):
        return True
    return os.environ.get("SMARTSERVE_ALLOW_MIRROR_WRITES") == "1"


@event.listens_for(Session, "before_flush")
def reject_mirror_writes(session: Session, flush_context: object, instances: object) -> None:
    if _mirror_writes_allowed(session):
        return
    blocked: list[str] = []
    for obj in session.new:
        if isinstance(obj, ReadOnlyMirror):
            blocked.append(type(obj).__name__)
    for obj in session.deleted:
        if isinstance(obj, ReadOnlyMirror):
            blocked.append(type(obj).__name__)
    for obj in session.dirty:
        if isinstance(obj, ReadOnlyMirror) and session.is_modified(obj, include_collections=False):
            blocked.append(type(obj).__name__)
    if blocked:
        raise ReadOnlyMirrorError("refusing to write read-only mirror rows: " + ", ".join(blocked))
