from django.apps import apps

from dj_lite_tenant.conf import is_tenant_app_or_model
from dj_lite_tenant.middleware import get_current_tenant_pk
from dj_lite_tenant.utils import get_tenant_db_alias, is_tenant_db_alias


class TenantDatabaseRouter:
    """
    Routes models listed in DJ_LITE_TENANT["APPS"] to the current tenant's SQLite database alias.
    All other models fall through to 'default'.
    """

    def db_for_read(self, model, **hints):  # noqa: ARG002
        if is_tenant_app_or_model(model._meta.app_label, model._meta.model_name):
            tenant_pk = get_current_tenant_pk()

            if tenant_pk is not None:
                return get_tenant_db_alias(tenant_pk)

            return None

        return "default"

    def db_for_write(self, model, **hints):  # noqa: ARG002
        if is_tenant_app_or_model(model._meta.app_label, model._meta.model_name):
            tenant_pk = get_current_tenant_pk()

            if tenant_pk is not None:
                return get_tenant_db_alias(tenant_pk)

            return None

        return "default"

    def allow_relation(self, obj1, obj2, **hints):  # noqa: ARG002
        # Always permit. Tenant↔shared relations are valid because every tenant
        # DB has the shared DB ATTACHed to it. We cannot detect cross-tenant
        # pairs here (objects carry no DB alias), so blanket-allow and rely on
        # application code to never form cross-tenant relations.
        return True

    def allow_migrate(self, db, app_label, model_name=None, **hints):  # noqa: ARG002
        if model_name is not None:
            try:
                model = apps.get_model(app_label, model_name)
                is_tenant = is_tenant_app_or_model(model._meta.app_label, model._meta.model_name)
            except LookupError:
                is_tenant = is_tenant_app_or_model(app_label, model_name)
        else:
            is_tenant = is_tenant_app_or_model(app_label)

        if is_tenant_db_alias(db):
            return is_tenant

        if db == "default":
            return not is_tenant

        return None
