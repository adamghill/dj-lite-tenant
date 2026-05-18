from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Model
from django.utils.module_loading import import_string

DEFAULTS = {
    "DIR": None,
    "APPS": frozenset(),
    "ATTACHMENTS": {"default": "shared"},
    "DB_NAME_PATTERN": "tenant_{tenant_pk}.sqlite3",
    "MAX_OPEN_CONNECTIONS": 100,
    "USE_DATABASE_TEMPLATE": False,
    "DELETE_TENANT_DB_ON_DELETE": False,
    "TENANT_MODEL": None,
    "TENANT_ID_CALLABLE": "dj_lite_tenant.middleware.get_tenant_pk_from_request",
    "TENANT_SETTINGS": {
        "CONN_MAX_AGE": 0,
        "CONN_HEALTH_CHECKS": False,
        "TIME_ZONE": None,
        "AUTOCOMMIT": True,
        "ATOMIC_REQUESTS": False,
        "TEST": {"NAME": None},
    },
}


def is_tenant_app_or_model(app_label: str, model_name: str | None = None) -> bool:
    """Returns True if app_label or app_label.model_name is in DJ_LITE_TENANT['APPS']."""

    tenant_apps = get_conf("APPS")

    if app_label in tenant_apps:
        return True

    if model_name is not None and f"{app_label}.{model_name}" in tenant_apps:
        return True

    return False


def get_conf(key):
    """
    Returns the value for the given key from DJ_LITE_TENANT settings.

    If the key is not found, returns the default value from DEFAULTS.
    """

    user_conf = getattr(settings, "DJ_LITE_TENANT", {})
    value = user_conf.get(key, DEFAULTS[key])

    if key == "DIR" and value is None:
        raise ImproperlyConfigured("DJ_LITE_TENANT['DIR'] must be set.")

    return value


def get_tenant_model() -> type[Model]:
    """
    Returns the tenant model class.

    DJ_LITE_TENANT['TENANT_MODEL'] may be:
    - None (default) — returns Django's active user model via get_user_model().
    - A 'app_label.ModelName' string — resolved via apps.get_model().
    """

    value = get_conf("TENANT_MODEL")

    if value is None:
        return get_user_model()

    return apps.get_model(value)


def get_tenant_id_callable():
    """
    Returns the tenant-ID callable.

    DJ_LITE_TENANT['TENANT_ID_CALLABLE'] must be a dotted-path string pointing
    to a callable(request) -> str | None.
    """

    value = get_conf("TENANT_ID_CALLABLE")

    return import_string(value)
