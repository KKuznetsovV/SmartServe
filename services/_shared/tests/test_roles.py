from smartserve_shared.roles import ROLE_RANK, ROLES, can_assign_role, can_manage_user


def test_roles_match_rank_keys() -> None:
    assert set(ROLES) == set(ROLE_RANK)
    assert ROLES == ("owner", "manager", "cashier", "waiter", "kitchen")


def test_manager_cannot_assign_owner_or_manager() -> None:
    assert not can_assign_role("manager", "owner")
    assert not can_assign_role("manager", "manager")
    assert can_assign_role("manager", "cashier")
    assert can_assign_role("manager", "waiter")
    assert can_assign_role("manager", "kitchen")


def test_owner_can_assign_owner_and_below() -> None:
    assert can_assign_role("owner", "owner")
    assert can_assign_role("owner", "manager")
    assert can_assign_role("owner", "kitchen")


def test_unknown_role_is_rejected() -> None:
    assert not can_assign_role("manager", "superadmin")
    assert not can_manage_user("superadmin", "waiter")
