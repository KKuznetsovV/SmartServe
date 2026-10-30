from smartserve_shared.db import Base as Base
from smartserve_shared.db import make_db_session, make_engine, make_get_db, make_sessionmaker

from app.core.config import settings

engine = make_engine(settings.DATABASE_URL, echo=settings.ENVIRONMENT == "development")
AsyncSessionLocal = make_sessionmaker(engine)
get_db = make_get_db(lambda: AsyncSessionLocal)
DbSession = make_db_session(get_db)
