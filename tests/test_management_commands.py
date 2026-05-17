from io import StringIO
from unittest.mock import patch

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.core.management.base import CommandError

# ---------------------------------------------------------------------------
# create_tenant_db
# ---------------------------------------------------------------------------


@pytest.mark.django_db
def test_create_tenant_db_unknown_user():
    """Raises CommandError when the user does not exist."""
    with pytest.raises(CommandError, match="does not exist"):
        call_command("create_tenant_db", "99999")


@pytest.mark.django_db
def test_create_tenant_db_success(allow_all_databases, testapp_migrations):
    """Creates and migrates a tenant DB for an existing user."""
    user = User.objects.create_user(username="cmd_user", password="pass")

    stdout = StringIO()

    setup_path = "dj_lite_tenant.management.commands.create_tenant_db.setup_tenant_db"

    with patch(setup_path, return_value=True) as mock_setup:
        call_command("create_tenant_db", str(user.pk), stdout=stdout)

    mock_setup.assert_called_once_with(str(user.pk))
    assert "ready" in stdout.getvalue()


@pytest.mark.django_db
def test_create_tenant_db_setup_failure(allow_all_databases):
    """Raises CommandError when setup_tenant_db returns False."""
    user = User.objects.create_user(username="cmd_fail_user", password="pass")

    with patch("dj_lite_tenant.management.commands.create_tenant_db.setup_tenant_db", return_value=False):
        with pytest.raises(CommandError, match="Failed to set up"):
            call_command("create_tenant_db", str(user.pk))


# ---------------------------------------------------------------------------
# migrate_tenant_dbs
# ---------------------------------------------------------------------------


def test_migrate_tenant_dbs_dir_missing(tmp_path, monkeypatch):
    """Writes to stderr and returns early when DIR does not exist."""
    from django.conf import settings

    nonexistent = tmp_path / "no_such_dir"
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "DIR": nonexistent})

    stderr = StringIO()
    call_command("migrate_tenant_dbs", stderr=stderr)

    assert "does not exist" in stderr.getvalue()


def test_migrate_tenant_dbs_no_files(tmp_path, monkeypatch):
    """Reports no databases found when DIR is empty."""
    from django.conf import settings

    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "DIR": tmp_path})

    stdout = StringIO()
    call_command("migrate_tenant_dbs", stdout=stdout)

    assert "No tenant databases found" in stdout.getvalue()


def test_migrate_tenant_dbs_ignores_non_matching_files(tmp_path, monkeypatch):
    """Files that don't match DB_NAME_PATTERN are ignored."""
    from django.conf import settings

    (tmp_path / "default.sqlite3").touch()
    (tmp_path / "something_else.db").touch()
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "DIR": tmp_path})

    stdout = StringIO()
    call_command("migrate_tenant_dbs", stdout=stdout)

    assert "No tenant databases found" in stdout.getvalue()


def test_migrate_tenant_dbs_calls_setup_for_each_match(tmp_path, monkeypatch):
    """Calls setup_tenant_db for each matching file, reports ok/failed counts."""
    from django.conf import settings

    (tmp_path / "tenant_42.sqlite3").touch()
    (tmp_path / "tenant_99.sqlite3").touch()
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "DIR": tmp_path})

    stdout = StringIO()

    with patch(
        "dj_lite_tenant.management.commands.migrate_tenant_dbs.setup_tenant_db",
        return_value=True,
    ) as mock_setup:
        call_command("migrate_tenant_dbs", stdout=stdout)

    assert mock_setup.call_count == 2
    called_pks = {call.args[0] for call in mock_setup.call_args_list}
    assert called_pks == {"42", "99"}

    output = stdout.getvalue()
    assert "2 ok" in output
    assert "0 failed" in output


def test_migrate_tenant_dbs_reports_failures(tmp_path, monkeypatch):
    """Failed setups are counted and reported."""
    from django.conf import settings

    (tmp_path / "tenant_7.sqlite3").touch()
    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "DIR": tmp_path})

    stdout = StringIO()

    with patch(
        "dj_lite_tenant.management.commands.migrate_tenant_dbs.setup_tenant_db",
        return_value=False,
    ):
        call_command("migrate_tenant_dbs", stdout=stdout)

    output = stdout.getvalue()
    assert "0 ok" in output
    assert "1 failed" in output


def test_migrate_tenant_dbs_custom_pattern(tmp_path, monkeypatch):
    """Regex is derived from DB_NAME_PATTERN, not hardcoded."""
    from django.conf import settings

    monkeypatch.setattr(
        settings,
        "DJ_LITE_TENANT",
        {**settings.DJ_LITE_TENANT, "DIR": tmp_path, "DB_NAME_PATTERN": "db_{tenant_pk}.sqlite3"},
    )

    (tmp_path / "db_abc123.sqlite3").touch()
    (tmp_path / "tenant_abc123.sqlite3").touch()  # old pattern — should be ignored

    stdout = StringIO()

    with patch(
        "dj_lite_tenant.management.commands.migrate_tenant_dbs.setup_tenant_db",
        return_value=True,
    ) as mock_setup:
        call_command("migrate_tenant_dbs", stdout=stdout)

    assert mock_setup.call_count == 1
    assert mock_setup.call_args.args[0] == "abc123"


# ---------------------------------------------------------------------------
# _build_tenant_db_re (unit tests for the helper)
# ---------------------------------------------------------------------------


def test_build_tenant_db_re_matches_default_pattern():
    from dj_lite_tenant.management.commands.migrate_tenant_dbs import _build_tenant_db_re

    regex = _build_tenant_db_re()
    assert regex.match("tenant_42.sqlite3")
    assert regex.match("tenant_abc-def.sqlite3")
    assert not regex.match("user_42.sqlite3")
    assert not regex.match("tenant_42.db")


def test_build_tenant_db_re_captures_tenant_pk():
    from dj_lite_tenant.management.commands.migrate_tenant_dbs import _build_tenant_db_re

    regex = _build_tenant_db_re()
    m = regex.match("tenant_hello-world.sqlite3")
    assert m is not None
    assert m.group(1) == "hello-world"


def test_build_tenant_db_re_raises_when_tenant_pk_missing(monkeypatch):
    """Raises ImproperlyConfiguredError when DB_NAME_PATTERN lacks {tenant_pk}."""
    from django.conf import settings
    from django.core.exceptions import ImproperlyConfigured as ImproperlyConfiguredError

    from dj_lite_tenant.management.commands.migrate_tenant_dbs import _build_tenant_db_re

    monkeypatch.setattr(
        settings,
        "DJ_LITE_TENANT",
        {**settings.DJ_LITE_TENANT, "DB_NAME_PATTERN": "tenant.sqlite3"},
    )

    with pytest.raises(ImproperlyConfiguredError, match="tenant_pk"):
        _build_tenant_db_re()
