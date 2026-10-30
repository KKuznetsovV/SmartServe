import pytest
from smartserve_shared.mirrors import ReadOnlyMirrorError

from app.db.models import Business


@pytest.mark.asyncio
async def test_read_only_mirror_rejects_unflagged_insert(db, monkeypatch):
    monkeypatch.delenv("SMARTSERVE_ALLOW_MIRROR_WRITES", raising=False)
    db.info["allow_mirror_writes"] = False
    db.add(Business(name="Blocked", country="IL", currency="ILS"))
    with pytest.raises(ReadOnlyMirrorError):
        await db.flush()
