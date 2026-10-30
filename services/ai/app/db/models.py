"""AI-owned tables. The assistant is otherwise stateless; `ai_outbox` holds audit events."""

from smartserve_shared.outbox import declare_outbox

from app.db.session import Base

Outbox = declare_outbox(Base, "ai_outbox")
