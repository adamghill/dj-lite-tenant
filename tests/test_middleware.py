from unittest.mock import MagicMock, patch

from dj_lite_tenant.middleware import (
    TenantDatabaseMiddleware,
    get_current_tenant_pk,
    get_tenant_pk_from_request,
)

_PATCH = "dj_lite_tenant.middleware.get_or_create_tenant_db"


def test_get_current_tenant_pk_default():
    assert get_current_tenant_pk() is None


def test_middleware_sets_tenant_pk():
    user = MagicMock()
    user.pk = 7
    user.is_authenticated = True
    user.is_superuser = False

    request = MagicMock()
    request.user = user
    request.session = {}

    responses = []

    def get_response(req):
        responses.append(get_current_tenant_pk())
        return MagicMock()

    with patch(_PATCH):
        middleware = TenantDatabaseMiddleware(get_response)
        middleware(request)

    assert responses == ["7"]
    assert get_current_tenant_pk() is None


def test_middleware_clears_tenant_pk_after_request():
    user = MagicMock()
    user.id = 42
    user.is_authenticated = True
    user.is_superuser = False

    request = MagicMock()
    request.user = user
    request.session = {}

    def get_response(req):
        return MagicMock()

    with patch(_PATCH):
        TenantDatabaseMiddleware(get_response)(request)

    assert get_current_tenant_pk() is None


def test_get_tenant_pk_from_request_authenticated():
    user = MagicMock()
    user.pk = 99
    user.is_authenticated = True
    user.is_superuser = False

    request = MagicMock()
    request.user = user
    request.session = {}

    assert get_tenant_pk_from_request(request) == "99"


def test_get_tenant_pk_from_request_anonymous():
    user = MagicMock()
    user.is_authenticated = False

    request = MagicMock()
    request.user = user

    assert get_tenant_pk_from_request(request) is None


def test_get_tenant_pk_from_request_superuser_session():
    user = MagicMock()
    user.is_authenticated = True
    user.is_superuser = True

    request = MagicMock()
    request.user = user
    request.session = {"admin_tenant_id": "42"}

    assert get_tenant_pk_from_request(request) == "42"


def test_middleware_custom_tenant_id_callable(monkeypatch):
    """Middleware delegates to a custom TENANT_ID_CALLABLE from settings."""
    from django.conf import settings

    captured = []

    monkeypatch.setattr(
        settings,
        "DJ_LITE_TENANT",
        {**settings.DJ_LITE_TENANT, "TENANT_ID_CALLABLE": "tests.test_middleware._custom_callable"},
    )

    request = MagicMock()

    def get_response(req):
        captured.append(get_current_tenant_pk())
        return MagicMock()

    with patch(_PATCH):
        middleware = TenantDatabaseMiddleware(get_response)
        middleware(request)

    assert captured == ["custom-tenant-pk"]


def _custom_callable(request):
    return "custom-tenant-pk"


def test_middleware_anonymous_user():
    user = MagicMock()
    user.is_authenticated = False

    request = MagicMock()
    request.user = user
    request.session = {}

    captured = []

    def get_response(req):
        captured.append(get_current_tenant_pk())
        return MagicMock()

    with patch(_PATCH):
        TenantDatabaseMiddleware(get_response)(request)

    assert captured == [None]
