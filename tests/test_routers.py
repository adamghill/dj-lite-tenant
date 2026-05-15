from unittest.mock import patch

from django_sqlite_tenant.routers import TenantDatabaseRouter, _is_tenant_model
from tests.testapp.models import UserNote


def test_is_tenant_model_by_app_label():
    assert _is_tenant_model(UserNote) is True


def test_is_tenant_model_false_for_auth():
    from django.contrib.auth.models import User
    assert _is_tenant_model(User) is False


def test_db_for_read_tenant_model():
    router = TenantDatabaseRouter()
    with patch("django_sqlite_tenant.routers.get_current_user_id", return_value=5):
        result = router.db_for_read(UserNote)
    assert result == "user_5"


def test_db_for_read_no_user():
    router = TenantDatabaseRouter()
    with patch("django_sqlite_tenant.routers.get_current_user_id", return_value=None):
        result = router.db_for_read(UserNote)
    assert result == "default"


def test_db_for_read_non_tenant():
    from django.contrib.auth.models import User
    router = TenantDatabaseRouter()
    with patch("django_sqlite_tenant.routers.get_current_user_id", return_value=5):
        result = router.db_for_read(User)
    assert result == "default"


def test_allow_migrate_user_db_tenant_app():
    router = TenantDatabaseRouter()
    assert router.allow_migrate("user_5", "testapp") is True


def test_allow_migrate_default_non_tenant():
    router = TenantDatabaseRouter()
    assert router.allow_migrate("default", "auth") is True


def test_allow_migrate_default_tenant_app():
    router = TenantDatabaseRouter()
    assert router.allow_migrate("default", "testapp") is False
