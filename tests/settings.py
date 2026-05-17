import tempfile
from pathlib import Path

BASE_DIR = Path(tempfile.mkdtemp())

SECRET_KEY = "dj-lite-tenant-test-secret"

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "dj_lite_tenant",
    "tests.testapp",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "dj_lite_tenant.middleware.TenantDatabaseMiddleware",
]

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "default.sqlite3",
    }
}

DATABASE_ROUTERS = ["dj_lite_tenant.routers.TenantDatabaseRouter"]

DJ_LITE_TENANT = {
    "DIR": BASE_DIR / "users",
    "APPS": {"testapp"},
    "ATTACHMENTS": {"default": "shared"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

USE_TZ = True

ROOT_URLCONF = "tests.urls"
