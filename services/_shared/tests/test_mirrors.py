from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

from smartserve_shared.mirrors import ReadOnlyMirror, ReadOnlyMirrorError


class _Base(DeclarativeBase):
    pass


class _MirrorRow(ReadOnlyMirror, _Base):
    __tablename__ = "read_only_mirror_rows"

    id: Mapped[str] = mapped_column(String, primary_key=True)


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    _Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def test_read_only_mirror_rejects_insert(session: Session) -> None:
    session.add(_MirrorRow(id="1"))
    with pytest.raises(ReadOnlyMirrorError):
        session.flush()


def test_read_only_mirror_allows_flagged_session(session: Session) -> None:
    session.info["allow_mirror_writes"] = True
    session.add(_MirrorRow(id="1"))
    session.flush()
    assert session.get(_MirrorRow, "1") is not None


def test_guard_cannot_be_disabled_by_environment(session: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SMARTSERVE_ALLOW_MIRROR_WRITES", "1")
    session.add(_MirrorRow(id="env"))
    with pytest.raises(ReadOnlyMirrorError):
        session.flush()
