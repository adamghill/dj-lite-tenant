from django_sqlite_tenant.conf import get_conf
from django_sqlite_tenant.middleware import get_current_user_id


def _is_tenant_model(model) -> bool:
    """
    Returns True if the model should be stored in the per-user DB.

    Two ways to mark a model as tenant-specific:
    1. Its app_label is in DJANGO_SQLITE_TENANT["APP_LABELS"] (settings-driven, preferred)
    2. The model class has _is_user_model = True (compatibility with dsud)
    """
    if getattr(model, "_is_user_model", False):
        return True
    app_labels = get_conf("APP_LABELS")
    return model._meta.app_label in app_labels


class TenantDatabaseRouter:
    """
    Routes models listed in DJANGO_SQLITE_TENANT["APP_LABELS"] (or flagged with
    _is_user_model = True) to the current user's SQLite database alias.
    All other models fall through to 'default'.
    """

    def db_for_read(self, model, **hints):
        if _is_tenant_model(model):
            user_id = get_current_user_id()
            if user_id is not None:
                return f"user_{user_id}"
        return "default"

    def db_for_write(self, model, **hints):
        if _is_tenant_model(model):
            user_id = get_current_user_id()
            if user_id is not None:
                return f"user_{user_id}"
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        t1 = _is_tenant_model(type(obj1))
        t2 = _is_tenant_model(type(obj2))
        if t1 == t2:
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        from django.apps import apps

        if model_name is not None:
            try:
                model = apps.get_model(app_label, model_name)
                is_tenant = _is_tenant_model(model)
            except LookupError:
                is_tenant = app_label in get_conf("APP_LABELS")
        else:
            is_tenant = app_label in get_conf("APP_LABELS")

        if db.startswith("user_"):
            return is_tenant
        if db == "default":
            return not is_tenant
        return None
