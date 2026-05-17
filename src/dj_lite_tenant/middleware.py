from contextlib import contextmanager
from contextvars import ContextVar

from dj_lite_tenant.conf import get_tenant_id_callable
from dj_lite_tenant.utils import close_tenant_db, get_or_create_tenant_db

_current_tenant_pk: ContextVar[str | None] = ContextVar("dj_lite_tenant_tenant_pk", default=None)


def get_current_tenant_pk() -> str | None:
    return _current_tenant_pk.get()


def get_tenant_pk_from_request(request) -> str | None:
    """Default TENANT_ID_CALLABLE: returns the tenant pk string for the current request."""
    if not hasattr(request, "user") or not request.user.is_authenticated:
        return None

    if request.user.is_superuser and "admin_tenant_id" in request.session:
        return str(request.session["admin_tenant_id"])

    return str(request.user.pk)


@contextmanager
def tenant_db(obj):
    """Context manager for out-of-request use: sets the current tenant and opens their DB."""
    tenant_pk = str(obj.pk)
    token = _current_tenant_pk.set(tenant_pk)
    get_or_create_tenant_db(tenant_pk)

    try:
        yield
    finally:
        _current_tenant_pk.reset(token)
        close_tenant_db(tenant_pk)


class TenantDatabaseMiddleware:
    """
    Middleware that sets the current tenant ID in a ContextVar so the router
    can direct queries to the correct per-tenant SQLite database.

    Must be placed after AuthenticationMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self._get_tenant_id = get_tenant_id_callable()

    def __call__(self, request):
        tenant_pk = self._get_tenant_id(request)
        token = _current_tenant_pk.set(tenant_pk)

        if tenant_pk is not None:
            get_or_create_tenant_db(tenant_pk)

        try:
            response = self.get_response(request)
        finally:
            _current_tenant_pk.reset(token)

        return response
