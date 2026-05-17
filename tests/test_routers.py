from unittest.mock import patch

from dj_lite_tenant.conf import is_tenant_app_or_model
from dj_lite_tenant.routers import TenantDatabaseRouter
from tests.testapp.models import UserNote


def test_is_tenant_model_by_app_label():
    assert is_tenant_app_or_model(UserNote._meta.app_label) is True


def test_is_tenant_model_false_for_auth():
    from django.contrib.auth.models import User

    assert is_tenant_app_or_model(User._meta.app_label) is False


def test_db_for_read_tenant_model():
    router = TenantDatabaseRouter()
    with patch("dj_lite_tenant.routers.get_current_tenant_pk", return_value="5"):
        result = router.db_for_read(UserNote)
    assert result == "tenant_5"


def test_db_for_read_no_tenant():
    router = TenantDatabaseRouter()
    with patch("dj_lite_tenant.routers.get_current_tenant_pk", return_value=None):
        result = router.db_for_read(UserNote)
    assert result is None


def test_db_for_read_non_tenant():
    from django.contrib.auth.models import User

    router = TenantDatabaseRouter()
    with patch("dj_lite_tenant.routers.get_current_tenant_pk", return_value="5"):
        result = router.db_for_read(User)
    assert result == "default"


def test_allow_migrate_default_non_tenant():
    router = TenantDatabaseRouter()
    assert router.allow_migrate("default", "auth") is True


def test_allow_migrate_default_tenant_app():
    router = TenantDatabaseRouter()
    assert router.allow_migrate("default", "testapp") is False
