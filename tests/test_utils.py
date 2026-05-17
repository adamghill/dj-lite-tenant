import os
from unittest.mock import patch

import pytest
from django.conf import settings

from dj_lite_tenant import connection_registry
from dj_lite_tenant.utils import (
    _build_tenant_db_config,
    _get_template_path,
    clear_template_cache,
    close_tenant_db,
    delete_tenant_db,
    get_attach_statements,
    get_tenant_db_alias,
    get_tenant_db_path,
    setup_tenant_db,
)


def test_get_tenant_db_alias():
    assert get_tenant_db_alias("42") == "tenant_42"


def test_get_tenant_db_path_contains_tenant_pk():
    path = get_tenant_db_path("99")
    assert "tenant_99" in str(path)
    assert str(path).endswith(".sqlite3")


def test_setup_and_delete_tenant_db(allow_all_databases, testapp_migrations):
    tenant_pk = "1001"
    result = setup_tenant_db(tenant_pk)
    assert result is True

    path = get_tenant_db_path(tenant_pk)
    assert os.path.exists(path)

    deleted = delete_tenant_db(tenant_pk)
    assert deleted is True
    assert not os.path.exists(path)


def test_setup_tenant_db_keeps_alias_on_success(allow_all_databases, testapp_migrations):
    """After a successful setup, the alias must remain in DATABASES and the connection registry."""
    tenant_pk = "2002"
    alias = get_tenant_db_alias(tenant_pk)

    result = setup_tenant_db(tenant_pk)
    assert result is True
    assert alias in settings.DATABASES
    assert connection_registry._registry.get(alias) is not None

    # Cleanup
    close_tenant_db(tenant_pk)


def test_get_attach_statements_multiple_aliases():
    """Verify multiple ATTACH statements are generated for multiple ATTACHMENTS."""

    with patch("dj_lite_tenant.utils.get_conf") as mock_get_conf:
        mock_get_conf.return_value = {
            "default": "shared",
            "archive": "old_data",
            "reference": "ref",
        }

        with patch.object(
            settings,
            "DATABASES",
            {
                "default": {"NAME": "/path/to/default.sqlite3"},
                "archive": {"NAME": "/path/to/archive.sqlite3"},
                "reference": {"NAME": "/path/to/reference.sqlite3"},
            },
        ):
            statements = get_attach_statements()

    assert len(statements) == 3
    assert "ATTACH DATABASE 'file:/path/to/default.sqlite3?mode=ro' AS \"shared\"" in statements
    assert "ATTACH DATABASE 'file:/path/to/archive.sqlite3?mode=ro' AS \"old_data\"" in statements
    assert "ATTACH DATABASE 'file:/path/to/reference.sqlite3?mode=ro' AS \"ref\"" in statements


def test_build_tenant_db_config_uses_dj_lite():
    """Verify _build_tenant_db_config uses dj-lite with custom backend override."""
    from pathlib import Path

    db_path = Path("/tmp/test_users/user_123.sqlite3")
    config = _build_tenant_db_config(db_path)

    assert config["ENGINE"] == "dj_lite_tenant.backends.sqlite3"
    assert config["NAME"] == db_path
    assert "OPTIONS" in config
    assert "init_command" in config["OPTIONS"]
    assert "PRAGMA journal_mode=WAL" in config["OPTIONS"]["init_command"]
    assert "PRAGMA synchronous=NORMAL" in config["OPTIONS"]["init_command"]
    assert "PRAGMA temp_store=MEMORY" in config["OPTIONS"]["init_command"]
    assert config["CONN_MAX_AGE"] == 0
    assert config["AUTOCOMMIT"] is True


def test_get_template_path_returns_dot_template_sqlite3(monkeypatch, isolated_tenant_dir):
    """_get_template_path should return .template.sqlite3 in the tenant dir."""
    template_path = _get_template_path()

    assert template_path.name == ".template.sqlite3"
    assert template_path.parent == isolated_tenant_dir


def test_clear_template_cache_removes_file(isolated_tenant_dir):
    """clear_template_cache should remove the template file if it exists."""
    template_path = isolated_tenant_dir / ".template.sqlite3"
    template_path.touch()

    assert template_path.exists()

    clear_template_cache()

    assert not template_path.exists()


def test_clear_template_cache_noop_when_no_file(isolated_tenant_dir):
    """clear_template_cache should not raise when template file does not exist."""
    template_path = isolated_tenant_dir / ".template.sqlite3"

    assert not template_path.exists()

    clear_template_cache()


@pytest.mark.django_db
def test_setup_tenant_db_creates_template_when_cache_enabled(
    allow_all_databases, testapp_migrations, monkeypatch, isolated_tenant_dir
):
    """When USE_DATABASE_TEMPLATE is True, first setup creates a template file."""
    new_conf = {**settings.DJ_LITE_TENANT, "USE_DATABASE_TEMPLATE": True}
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", new_conf)

    tenant_pk = "3003"
    template_path = isolated_tenant_dir / ".template.sqlite3"

    assert not template_path.exists()

    result = setup_tenant_db(tenant_pk)

    assert result is True
    assert template_path.exists()

    close_tenant_db(tenant_pk)


def test_setup_tenant_db_uses_template_when_available(
    allow_all_databases, testapp_migrations, monkeypatch, isolated_tenant_dir
):
    """When template exists and USE_DATABASE_TEMPLATE is True, copy template instead of migrate."""
    new_conf = {**settings.DJ_LITE_TENANT, "USE_DATABASE_TEMPLATE": True}
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", new_conf)

    first_tenant = "4004"
    second_tenant = "4005"

    setup_tenant_db(first_tenant)
    template_path = isolated_tenant_dir / ".template.sqlite3"
    assert template_path.exists()

    with patch("dj_lite_tenant.utils.call_command") as mock_migrate:
        result = setup_tenant_db(second_tenant)

        assert result is True
        mock_migrate.assert_not_called()

    db_path = get_tenant_db_path(second_tenant)
    assert os.path.exists(db_path)

    close_tenant_db(second_tenant)


def test_setup_tenant_db_migrates_when_cache_disabled(
    allow_all_databases, testapp_migrations, monkeypatch, isolated_tenant_dir
):
    """When USE_DATABASE_TEMPLATE is False (default), always run migrations."""
    new_conf = {**settings.DJ_LITE_TENANT, "USE_DATABASE_TEMPLATE": False}
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", new_conf)

    tenant_pk = "5005"

    with patch("dj_lite_tenant.utils.call_command") as mock_migrate:
        result = setup_tenant_db(tenant_pk)

        assert result is True
        mock_migrate.assert_called_once()

    close_tenant_db(tenant_pk)


def test_setup_tenant_db_falls_back_to_migrate_on_copy_failure(
    allow_all_databases, testapp_migrations, monkeypatch, isolated_tenant_dir
):
    """If template copy fails, fallback to running migrations."""
    new_conf = {**settings.DJ_LITE_TENANT, "USE_DATABASE_TEMPLATE": True}
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", new_conf)

    template_path = isolated_tenant_dir / ".template.sqlite3"
    template_path.touch()

    tenant_pk = "6006"

    with patch("shutil.copyfile") as mock_copy:
        mock_copy.side_effect = OSError("Permission denied")

        with patch("dj_lite_tenant.utils.call_command") as mock_migrate:
            result = setup_tenant_db(tenant_pk)

            assert result is True
            mock_migrate.assert_called_once()

    close_tenant_db(tenant_pk)
