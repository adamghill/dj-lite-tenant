from unittest.mock import MagicMock, patch

from django_sqlite_tenant.middleware import (
    TenantDatabaseMiddleware,
    get_current_user_id,
)

_PATCH = "django_sqlite_tenant.middleware.get_or_create_user_db"


def test_get_current_user_id_default():
    assert get_current_user_id() is None


def test_middleware_sets_user_id():
    user = MagicMock()
    user.id = 7
    user.is_authenticated = True
    user.is_superuser = False

    request = MagicMock()
    request.user = user
    request.session = {}

    responses = []

    def get_response(req):
        responses.append(get_current_user_id())
        return MagicMock()

    with patch(_PATCH):
        middleware = TenantDatabaseMiddleware(get_response)
        middleware(request)

    assert responses == [7]
    assert get_current_user_id() is None


def test_middleware_clears_user_id_after_request():
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

    assert get_current_user_id() is None


def test_middleware_anonymous_user():
    user = MagicMock()
    user.is_authenticated = False

    request = MagicMock()
    request.user = user
    request.session = {}

    captured = []

    def get_response(req):
        captured.append(get_current_user_id())
        return MagicMock()

    with patch(_PATCH):
        TenantDatabaseMiddleware(get_response)(request)

    assert captured == [None]
