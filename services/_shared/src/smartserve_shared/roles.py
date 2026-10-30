"""Staff roles and rank used by auth/staff schemas and hierarchy checks."""

from typing import Literal, get_args

Role = Literal["owner", "manager", "cashier", "waiter", "kitchen"]
ROLES: tuple[Role, ...] = get_args(Role)

ROLE_RANK: dict[str, int] = {
    "owner": 4,
    "manager": 3,
    "cashier": 2,
    "waiter": 1,
    "kitchen": 0,
}


def can_assign_role(actor_role: str, target_role: str) -> bool:
    """True when the actor may create or assign `target_role`."""
    if actor_role not in ROLE_RANK or target_role not in ROLE_RANK:
        return False
    if actor_role == "owner" and target_role == "owner":
        return True
    return ROLE_RANK[target_role] < ROLE_RANK[actor_role]


def can_manage_user(actor_role: str, target_role: str) -> bool:
    """True when the actor may update a user who currently has `target_role`."""
    return can_assign_role(actor_role, target_role)
