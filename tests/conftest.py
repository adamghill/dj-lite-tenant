import os
import shutil

import pytest
from django.conf import settings
from django.core.management import call_command
from django.db import connections

from dj_lite_tenant import connection_registry
from dj_lite_tenant.utils import is_tenant_db_alias


@pytest.fixture(scope="function")
def testapp_migrations(django_db_setup, django_db_blocker):
    """
    Generate fresh migrations for testapp at test start.
    Cleanup must be done in the test itself to avoid breaking other tests.
    """

    import sys

    mig_dir = os.path.join(os.path.dirname(__file__), "testapp", "migrations")

    if os.path.exists(mig_dir):
        shutil.rmtree(mig_dir)
    os.makedirs(mig_dir)

    with open(os.path.join(mig_dir, "__init__.py"), "w"):
        pass

    # Clear migration cache so Django sees the new files
    if "tests.testapp.migrations" in sys.modules:
        del sys.modules["tests.testapp.migrations"]

    # makemigrations checks migration history, which requires DB access
    with django_db_blocker.unblock():
        call_command("makemigrations", "testapp", verbosity=0)

    yield mig_dir


@pytest.fixture
def allow_all_databases(django_db_setup, django_db_blocker):
    """Allow queries to dynamically-created database aliases (e.g. user_*)."""

    with django_db_blocker.unblock():
        yield
        _delete_users_in_default_db()


@pytest.fixture(autouse=True)
def _close_tenant_connections_after_each_test():
    """
    Always close tenant DB connections after every test.

    Tenant connections hold an ATTACH-RO lock on the default DB. If those
    connections leak across tests, subsequent writes to the default DB
    (e.g. django_session) hit SQLITE_LOCKED ("database table is locked").
    """

    yield
    _close_all_tenant_connections()


def _close_all_tenant_connections() -> None:
    """Close every tenant DB connection and drop its alias from settings."""

    tenant_aliases = [alias for alias in list(settings.DATABASES) if is_tenant_db_alias(alias)]

    for alias in tenant_aliases:
        if alias in connections.databases:
            try:
                connections[alias].close()
            except Exception:  # noqa: BLE001
                pass
            try:
                del connections[alias]
            except Exception:  # noqa: BLE001
                pass

        settings.DATABASES.pop(alias, None)

    connection_registry.clear()


def _delete_users_in_default_db() -> None:
    """Remove users created outside of pytest-django's transaction wrapper."""

    with connections["default"].cursor() as cur:
        cur.execute("PRAGMA foreign_keys = OFF")
        cur.execute("DELETE FROM auth_user")
        cur.execute("PRAGMA foreign_keys = ON")


@pytest.fixture
def isolated_tenant_dir(tmp_path, monkeypatch):
    """
    Point DJ_LITE_TENANT['DIR'] at a fresh tmp directory for the test
    so on-disk artifacts can be inspected without polluting other tests.
    """

    tenant_dir = tmp_path / "tenants"
    tenant_dir.mkdir()
    new_conf = {**settings.DJ_LITE_TENANT, "DIR": tenant_dir}
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", new_conf)

    yield tenant_dir
