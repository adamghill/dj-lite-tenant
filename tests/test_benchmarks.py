"""
pytest-benchmark microbenchmarks for dj-lite-tenant hot paths.

Run with:
    uv run pytest tests/test_benchmarks.py --benchmark-only -v

These benchmarks do perform real migrations and file I/O for setup, but the
benchmarked code paths themselves measure pure Python / registry overhead.

Benchmark groups:
- db_provisioning: Creating and looking up tenant databases
- context_manager: tenant_db() context manager overhead
- registry: LRU connection registry operations
"""

import os
import shutil

import pytest

from dj_lite_tenant import connection_registry

# =============================================================================
# DB Provisioning Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="db_provisioning")
def test_bench_get_or_create_tenant_db_hot(
    benchmark, isolated_tenant_dir, testapp_migrations, allow_all_databases  # noqa: ARG001
):
    """
    Hot path: `get_or_create_tenant_db` when DB already exists.
    Measures registry lookup + alias registration overhead (no file creation).
    """

    from django.core.management import call_command  # noqa: PLC0415

    from dj_lite_tenant.utils import get_or_create_tenant_db  # noqa: PLC0415

    migrations_directory = testapp_migrations

    try:
        call_command("migrate", verbosity=0)
        tenant_pk = "bench-hot-1"
        get_or_create_tenant_db(tenant_pk)  # Provision first (not benchmarked)

        benchmark.extra_info["path"] = "hot"
        benchmark(get_or_create_tenant_db, tenant_pk)
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


@pytest.mark.benchmark(group="db_provisioning")
def test_bench_get_or_create_tenant_db_cold(
    benchmark, isolated_tenant_dir, testapp_migrations, allow_all_databases  # noqa: ARG001
):
    """
    Cold path: `get_or_create_tenant_db` when DB does not exist.
    Measures full provisioning including template copy + migrations.
    """

    from django.core.management import call_command  # noqa: PLC0415

    from dj_lite_tenant.utils import delete_tenant_db, get_or_create_tenant_db  # noqa: PLC0415

    migrations_directory = testapp_migrations
    tenant_pk = "bench-cold-1"

    try:
        call_command("migrate", verbosity=0)

        benchmark.extra_info["path"] = "cold"
        benchmark(get_or_create_tenant_db, tenant_pk)
    finally:
        try:
            delete_tenant_db(tenant_pk)
        except (OSError, ValueError):
            pass  # Ignore cleanup errors
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


# =============================================================================
# Context Manager Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="context_manager")
def test_bench_tenant_db_context_manager_user(
    benchmark, isolated_tenant_dir, testapp_migrations, allow_all_databases  # noqa: ARG001
):
    """
    tenant_db() context manager with a User instance.
    Measures enter + exit overhead for model-based tenant lookup.
    """

    from django.contrib.auth.models import User  # noqa: PLC0415
    from django.core.management import call_command  # noqa: PLC0415

    from dj_lite_tenant.middleware import tenant_db  # noqa: PLC0415

    migrations_directory = testapp_migrations

    try:
        call_command("migrate", verbosity=0)
        user = User.objects.create_user(username="bench-ctx-user", password="pass")

        def _enter_exit():
            with tenant_db(user):
                pass

        benchmark.extra_info["lookup_type"] = "user_model"
        benchmark(_enter_exit)
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


@pytest.mark.benchmark(group="context_manager")
def test_bench_tenant_db_context_manager_fake_obj(
    benchmark, isolated_tenant_dir, testapp_migrations, allow_all_databases  # noqa: ARG001
):
    """
    tenant_db() context manager with a fake object (has .pk attribute).
    Measures enter + exit overhead for object-based lookup (same code path as User).
    """

    from django.core.management import call_command  # noqa: PLC0415

    from dj_lite_tenant.middleware import tenant_db  # noqa: PLC0415
    from dj_lite_tenant.utils import get_or_create_tenant_db  # noqa: PLC0415

    migrations_directory = testapp_migrations
    tenant_pk = "bench-ctx-obj"

    class FakeTenant:
        def __init__(self, pk):
            self.pk = pk

    fake_obj = FakeTenant(tenant_pk)

    try:
        call_command("migrate", verbosity=0)
        get_or_create_tenant_db(tenant_pk)  # Ensure DB exists

        def _enter_exit():
            with tenant_db(fake_obj):
                pass

        benchmark.extra_info["lookup_type"] = "fake_object"
        benchmark(_enter_exit)
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


# =============================================================================
# Connection Registry Benchmarks
# =============================================================================


@pytest.mark.benchmark(group="registry")
def test_bench_connection_registry_touch_only(benchmark, isolated_tenant_dir):  # noqa: ARG001
    """
    Registry touch() only - no eviction.
    Measures base LRU bookkeeping overhead.
    """

    aliases = [f"tenant_bench_{i}" for i in range(10)]

    def _touch_only():
        for alias in aliases:
            connection_registry.touch(alias)

    benchmark.extra_info["operation"] = "touch_only"
    benchmark(_touch_only)

    for alias in aliases:
        connection_registry.remove(alias)


@pytest.mark.benchmark(group="registry")
def test_bench_connection_registry_touch_evict(benchmark, isolated_tenant_dir):  # noqa: ARG001
    """
    Registry touch() + evict_if_needed() with small cap (5).
    Measures LRU bookkeeping with active eviction.
    """

    aliases = [f"tenant_bench_{i}" for i in range(10)]

    def _touch_and_evict():
        for alias in aliases:
            connection_registry.touch(alias)
            connection_registry.evict_if_needed(5)

    benchmark.extra_info["operation"] = "touch_with_evict"
    benchmark.extra_info["max_connections"] = 5
    benchmark(_touch_and_evict)

    for alias in aliases:
        connection_registry.remove(alias)
