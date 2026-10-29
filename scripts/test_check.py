from check import FRONTENDS, SERVICES, targets_from_changed


def test_gateway_and_shared_select_every_service():
    services, frontends, api = targets_from_changed(["services/gateway/nginx.conf"])
    assert services == set(SERVICES)
    assert not frontends
    assert not api

    services, _, _ = targets_from_changed(["services/_shared/src/jwt.py"])
    assert services == set(SERVICES)


def test_service_and_frontend_paths():
    services, frontends, api = targets_from_changed(
        [
            "services/payments/app/db/session.py",
            "apps/web/src/app/layout.tsx",
            "tests/api/test_s1.py",
        ]
    )
    assert services == {"payments"}
    assert frontends == {"web"}
    assert api


def test_packages_select_both_frontends():
    services, frontends, api = targets_from_changed(["packages/types/src/order.ts"])
    assert not services
    assert frontends == set(FRONTENDS)
    assert not api
