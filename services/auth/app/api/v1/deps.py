"""FastAPI dependencies for auth and DB session injection."""

from smartserve_shared.deps import make_auth_dependencies

from app.db.models import User
from app.db.session import get_db

get_current_user, require_role, require_manager, require_owner, require_staff = make_auth_dependencies(User, get_db)
