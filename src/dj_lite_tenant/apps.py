from django.apps import AppConfig
from django.db.models.signals import post_delete, post_save

from dj_lite_tenant.conf import get_tenant_model
from dj_lite_tenant.signals import (  # noqa: F401
    create_tenant_database,
    delete_tenant_database,
    invalidate_template_cache,
    on_connection_created,
)


class DjLiteTenantConfig(AppConfig):
    name = "dj_lite_tenant"
    verbose_name = "dj-lite-tenant"

    def ready(self):
        tenant_model = get_tenant_model()
        post_save.connect(create_tenant_database, sender=tenant_model)
        post_delete.connect(delete_tenant_database, sender=tenant_model)
