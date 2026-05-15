from django.conf import settings


DEFAULTS = {
    "DB_DIR": None,
    "APP_LABELS": set(),
    "CATALOG_ALIAS": "default",
    "CATALOG_ATTACH_NAME": "catalog",
    "SQLITE_INIT_COMMAND": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL; PRAGMA foreign_keys=ON;",
    "DB_NAME_PATTERN": "user_{user_id}.sqlite3",
    "CONN_MAX_AGE": 0,
}


def get_conf(key):
    user_conf = getattr(settings, "DJANGO_SQLITE_TENANT", {})
    value = user_conf.get(key, DEFAULTS[key])
    if key == "DB_DIR" and value is None:
        raise ImproperlyConfiguredError(
            "DJANGO_SQLITE_TENANT['DB_DIR'] must be set."
        )
    return value


class ImproperlyConfiguredError(Exception):
    pass
