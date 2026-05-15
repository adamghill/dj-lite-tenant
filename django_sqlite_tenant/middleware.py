from contextlib import contextmanager
from contextvars import ContextVar

from django_sqlite_tenant.utils import get_or_create_user_db, close_user_db

_current_user_id: ContextVar[int | None] = ContextVar("django_sqlite_tenant_user_id", default=None)


def get_current_user_id() -> int | None:
    return _current_user_id.get()


@contextmanager
def tenant_db(user):
    """Context manager for out-of-request use: sets the current user and opens their DB."""
    token = _current_user_id.set(user.id)
    get_or_create_user_db(user.id)
    try:
        yield
    finally:
        _current_user_id.reset(token)
        close_user_db(user.id)


class TenantDatabaseMiddleware:
    """
    Middleware that sets the current user ID in a ContextVar so the router
    can direct queries to the correct per-user SQLite database.

    Must be placed after AuthenticationMiddleware in MIDDLEWARE.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_id = None

        if hasattr(request, "user") and request.user.is_authenticated:
            if request.user.is_superuser and "admin_user_id" in request.session:
                user_id = request.session["admin_user_id"]
            else:
                user_id = request.user.id

        token = _current_user_id.set(user_id)

        if user_id is not None:
            get_or_create_user_db(user_id)

        try:
            response = self.get_response(request)
        finally:
            _current_user_id.reset(token)

        return response
