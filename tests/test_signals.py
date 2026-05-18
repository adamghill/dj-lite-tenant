from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.db.models.signals import post_save

from dj_lite_tenant.signals import create_tenant_database


def test_create_tenant_database_signal_connected_to_tenant_model():
    """create_tenant_database is connected to whatever get_tenant_model() returns."""

    all_receivers = [
        fn for group in post_save._live_receivers(User) for fn in (group if isinstance(group, list) else [group])
    ]
    assert create_tenant_database in all_receivers


def test_create_tenant_database_calls_setup(monkeypatch):
    """create_tenant_database calls setup_tenant_db with str(instance.pk) when created=True."""

    with patch("dj_lite_tenant.signals.setup_tenant_db") as mock_setup:
        instance = User(pk=42)
        create_tenant_database(sender=User, instance=instance, created=True)
        mock_setup.assert_called_once_with("42")


def test_create_tenant_database_skips_when_not_created():
    """create_tenant_database does nothing when created=False."""

    with patch("dj_lite_tenant.signals.setup_tenant_db") as mock_setup:
        instance = User(pk=42)
        create_tenant_database(sender=User, instance=instance, created=False)
        mock_setup.assert_not_called()


@pytest.mark.django_db
def test_signal_fires_on_user_create(allow_all_databases, isolated_tenant_dir, testapp_migrations):
    """Creating a User triggers create_tenant_database which calls setup_tenant_db."""

    with patch("dj_lite_tenant.signals.setup_tenant_db") as mock_setup:
        User.objects.create_user(username="sigtest", password="pass")

    mock_setup.assert_called_once()
    called_pk = mock_setup.call_args.args[0]
    assert isinstance(called_pk, str)
