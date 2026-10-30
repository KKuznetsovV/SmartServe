import pytest
from smartserve_shared.mirrors import ReadOnlyMirrorError

from app.db.models import Business


@pytest.mark.asyncio
async def test_app_session_rejects_mirror_write(db):
    db.info.pop("allow_mirror_writes", None)
    db.add(Business(name="Blocked", country="IL", currency="ILS"))
    with pytest.raises(ReadOnlyMirrorError):
        await db.flush()
