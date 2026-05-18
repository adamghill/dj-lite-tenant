import os
import shutil

import pytest
from django.conf import settings
from django.core.management import call_command


@pytest.fixture(scope="function")
def testapp_migrations():
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

    call_command("makemigrations", "testapp", verbosity=0)

    yield mig_dir


@pytest.fixture
def allow_all_databases(django_db_setup, django_db_blocker):
    """Allow queries to dynamically-created database aliases (e.g. user_*)."""

    with django_db_blocker.unblock():
        yield


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
