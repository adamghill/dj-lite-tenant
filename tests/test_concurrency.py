"""
Concurrency correctness tests for dj-lite-tenant.

All tests are marked `integration` because they create real tenant DB files
and exercise the full middleware / router / signal stack.

Three scenarios are covered:

1. Isolation — N concurrent threads, each a different tenant, write unique notes;
   after all threads finish no cross-tenant bleed is detectable.

2. Contention — M threads all write to the *same* tenant DB simultaneously;
   the final note count must equal M (validates SQLite WAL write-lock tolerance).

3. LRU eviction — MAX_OPEN_CONNECTIONS is patched to 3 while 5 tenants make
   concurrent requests; every tenant must remain queryable after eviction.
"""

import json
import os
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connections as django_connections
from django.test import Client


def _setup_users_and_migrations(n: int, prefix: str = "") -> list[User]:
    """Create *n* users; post_save signal provisions each tenant DB."""

    call_command("migrate", verbosity=0)

    users = []

    for i in range(n):
        users.append(User.objects.create_user(username=f"{prefix}concuser{i}", password="pass"))

    return users


def _post_note(user_id: int, text: str) -> int:
    """Create a fresh Django test Client, log in as *user_id*, POST a note.
    Returns the HTTP status code.
    """

    try:
        client = Client()
        user = User.objects.get(pk=user_id)
        client.force_login(user)

        resp = client.post(
            "/api/notes/",
            data=json.dumps({"text": text}),
            content_type="application/json",
        )

        return resp.status_code
    finally:
        django_connections.close_all()


def _get_notes(user_id: int) -> dict:
    """Log in as *user_id* and GET the notes API.  Returns the JSON payload."""

    try:
        client = Client()
        user = User.objects.get(pk=user_id)
        client.force_login(user)

        return client.get("/api/notes/").json()
    finally:
        django_connections.close_all()


@pytest.mark.integration
def test_concurrent_tenants_are_isolated(allow_all_databases, isolated_tenant_dir, testapp_migrations):
    """
    Isolation: N threads, each a different tenant, POST a unique note concurrently.
    After all threads finish, each tenant's GET must return exactly their own note.
    """

    migrations_directory = testapp_migrations

    try:
        n = 6
        prefix = uuid.uuid4().hex[:8]
        users = _setup_users_and_migrations(n, prefix=prefix)
        user_ids = [u.pk for u in users]

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = {
                pool.submit(_post_note, uid, f"note-for-{uid}"): uid
                for uid in user_ids
            }

            for future in as_completed(futures):
                assert future.result() == 201, "POST failed for user"

        for uid in user_ids:
            data = _get_notes(uid)
            notes = data["tenant_db"]["notes"]
            assert len(notes) == 1, f"User {uid} should have exactly 1 note, got {len(notes)}"
            assert notes[0]["text"] == f"note-for-{uid}", f"User {uid} saw wrong note: {notes[0]['text']}"
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


@pytest.mark.integration
def test_concurrent_writes_to_same_tenant(allow_all_databases, isolated_tenant_dir, testapp_migrations):
    """
    Contention: M threads all write to the same tenant DB simultaneously.
    Final note count must equal M — no writes lost, no crashes.
    """

    migrations_directory = testapp_migrations

    try:
        m = 8
        prefix = uuid.uuid4().hex[:8]
        call_command("migrate", verbosity=0)
        user = User.objects.create_user(username=f"{prefix}shareduser", password="pass")

        with ThreadPoolExecutor(max_workers=m) as pool:
            futures = [
                pool.submit(_post_note, user.pk, f"concurrent-note-{i}")
                for i in range(m)
            ]

            for future in as_completed(futures):
                assert future.result() == 201, "POST failed"

        data = _get_notes(user.pk)
        note_count = data["tenant_db"]["note_count"]
        assert note_count == m, f"Expected {m} notes, got {note_count}"
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


@pytest.mark.integration
def test_tenant_db_context_manager_concurrent(allow_all_databases, isolated_tenant_dir, testapp_migrations):
    """
    Verifies ContextVar isolation when tenant_db() is used concurrently outside
    of a request (background-task use case). Each thread opens its own tenant
    context; no thread should observe another tenant's ContextVar value.
    """

    from dj_lite_tenant.middleware import get_current_tenant_pk, tenant_db

    migrations_directory = testapp_migrations

    try:
        n = 6
        prefix = uuid.uuid4().hex[:8]
        users = _setup_users_and_migrations(n, prefix=prefix)

        observed_pks: dict[int, str | None] = {}
        lock = threading.Lock()

        def _check_context(user):
            with tenant_db(user):
                pk = get_current_tenant_pk()

            with lock:
                observed_pks[user.pk] = pk

            django_connections.close_all()

        with ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(_check_context, u) for u in users]

            for f in as_completed(futures):
                f.result()

        for user in users:
            assert observed_pks[user.pk] == str(user.pk), (
                f"User {user.pk} saw wrong tenant pk: {observed_pks[user.pk]}"
            )
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)


@pytest.mark.integration
def test_lru_eviction_does_not_lose_data(allow_all_databases, isolated_tenant_dir, testapp_migrations, monkeypatch):
    """
    LRU eviction: MAX_OPEN_CONNECTIONS=3 with 5 tenants.
    Interleaved concurrent requests must not lose any tenant's data even after
    connections are evicted and re-opened.
    """

    from django.conf import settings

    migrations_directory = testapp_migrations

    try:
        n = 5
        cap = 3

        monkeypatch.setattr(
            settings,
            "DJ_LITE_TENANT",
            {**settings.DJ_LITE_TENANT, "MAX_OPEN_CONNECTIONS": cap},
        )

        prefix = uuid.uuid4().hex[:8]
        users = _setup_users_and_migrations(n, prefix=prefix)
        user_ids = [u.pk for u in users]

        with ThreadPoolExecutor(max_workers=n) as pool:
            first_wave = {
                pool.submit(_post_note, uid, f"first-{uid}"): uid
                for uid in user_ids
            }

            for future in as_completed(first_wave):
                assert future.result() == 201

        with ThreadPoolExecutor(max_workers=n) as pool:
            second_wave = {
                pool.submit(_post_note, uid, f"second-{uid}"): uid
                for uid in user_ids
            }

            for future in as_completed(second_wave):
                assert future.result() == 201

        for uid in user_ids:
            data = _get_notes(uid)
            note_count = data["tenant_db"]["note_count"]
            assert note_count == 2, (
                f"User {uid}: expected 2 notes after eviction round-trip, got {note_count}"
            )
    finally:
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)
