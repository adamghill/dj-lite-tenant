from django.apps import AppConfig


class DjangoSQLiteTenantConfig(AppConfig):
    name = "django_sqlite_tenant"
    verbose_name = "Django SQLite Tenant"

    def ready(self):
        import django_sqlite_tenant.signals  # noqa: F401
