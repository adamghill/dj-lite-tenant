from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured as ImproperlyConfiguredError

from dj_lite_tenant.conf import (
    DEFAULTS,
    get_conf,
    get_tenant_id_callable,
    get_tenant_model,
    is_tenant_app_or_model,
)


def test_get_conf_defaults():
    assert get_conf("APPS") == {"testapp"}
    assert get_conf("ATTACHMENTS") == {"default": "shared"}
    assert get_conf("DB_NAME_PATTERN") == "tenant_{tenant_pk}.sqlite3"


def test_get_conf_db_dir_set():
    db_dir = get_conf("DIR")
    assert db_dir is not None


def test_get_conf_dir_not_set_raises_error():
    """Verify ImproperlyConfiguredError is raised when DIR is not configured."""

    with patch("django.conf.settings.DJ_LITE_TENANT", {}):
        with pytest.raises(ImproperlyConfiguredError, match="DIR.*must be set"):
            get_conf("DIR")


def test_init_command_removed_from_defaults():
    """INIT_COMMAND is no longer in defaults since dj-lite handles SQLite configuration."""

    assert "INIT_COMMAND" not in DEFAULTS


def test_options_defaults():
    """TENANT_SETTINGS should have defaults for database configuration."""

    options = DEFAULTS["TENANT_SETTINGS"]
    assert options["CONN_MAX_AGE"] == 0
    assert options["CONN_HEALTH_CHECKS"] is False
    assert options["TIME_ZONE"] is None
    assert options["AUTOCOMMIT"] is True
    assert options["ATOMIC_REQUESTS"] is False
    assert options["TEST"] == {"NAME": None}


def test_options_override_from_settings():
    """User should be able to override TENANT_SETTINGS via settings."""

    assert get_conf("TENANT_SETTINGS")["AUTOCOMMIT"] is True


def test_is_tenant_app_or_model_by_app_label():
    """Returns True when app_label is in APPS."""

    assert is_tenant_app_or_model("testapp") is True


def test_is_tenant_app_or_model_false():
    """Returns False when neither app_label nor app_label.model_name is in APPS."""

    assert is_tenant_app_or_model("auth") is False
    assert is_tenant_app_or_model("auth", "User") is False


def test_get_tenant_model_default_returns_user_model():
    """get_tenant_model() returns the active user model by default."""

    assert get_tenant_model() is get_user_model()


def test_get_tenant_model_string_setting(monkeypatch):
    """get_tenant_model() resolves a 'app_label.ModelName' string."""

    from django.conf import settings
    from django.contrib.auth.models import User

    monkeypatch.setattr(settings, "DJ_LITE_TENANT", {**settings.DJ_LITE_TENANT, "TENANT_MODEL": "auth.User"})
    assert get_tenant_model() is User


def test_get_tenant_id_callable_default_returns_builtin():
    """get_tenant_id_callable() returns the built-in request extractor by default."""

    from dj_lite_tenant.middleware import get_tenant_pk_from_request

    assert get_tenant_id_callable() is get_tenant_pk_from_request


def test_get_tenant_id_callable_custom(monkeypatch):
    """get_tenant_id_callable() imports and returns a custom callable."""

    from django.conf import settings

    monkeypatch.setattr(
        settings,
        "DJ_LITE_TENANT",
        {**settings.DJ_LITE_TENANT, "TENANT_ID_CALLABLE": "dj_lite_tenant.middleware.get_tenant_pk_from_request"},
    )
    from dj_lite_tenant.middleware import get_tenant_pk_from_request

    assert get_tenant_id_callable() is get_tenant_pk_from_request


def test_is_tenant_app_or_model_by_model_name():
    """Returns True when app_label.model_name format is in APPS."""

    with patch("django.conf.settings.DJ_LITE_TENANT", {"APPS": {"testapp.Note"}}):
        # app_label alone should not match
        assert is_tenant_app_or_model("testapp") is False

        # app_label.model_name should match
        assert is_tenant_app_or_model("testapp", "Note") is True

        # Different model in same app should not match
        assert is_tenant_app_or_model("testapp", "Other") is False
