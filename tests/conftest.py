import pytest


@pytest.fixture
def allow_all_databases(django_db_setup, django_db_blocker):
    """Allow queries to dynamically-created database aliases (e.g. user_*)."""
    with django_db_blocker.unblock():
        yield
