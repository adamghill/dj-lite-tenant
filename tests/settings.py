import tempfile
from pathlib import Path

BASE_DIR = Path(tempfile.mkdtemp())

SECRET_KEY = "django-sqlite-tenant-test-secret"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django_sqlite_tenant",
    "tests.testapp",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "default.sqlite3",
    }
}

DJANGO_SQLITE_TENANT = {
    "DB_DIR": BASE_DIR / "users",
    "APP_LABELS": {"testapp"},
    "CATALOG_ALIAS": "default",
    "CATALOG_ATTACH_NAME": "catalog",
    "SQLITE_INIT_COMMAND": "PRAGMA journal_mode=WAL;",
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True
