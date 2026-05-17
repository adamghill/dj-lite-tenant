import json
import os
import shutil

import pytest
from django.contrib.auth.models import User
from django.core.management import call_command


def _create_note_and_verify(client, user, text, expected_user_count):
    """Helper: POST a note as user, then GET and verify isolation + FK traversal."""
    client.force_login(user)

    post_response = client.post(
        "/api/notes/",
        data=json.dumps({"text": text}),
        content_type="application/json",
    )

    assert post_response.status_code == 201
    created = post_response.json()
    assert created["user_id"] == user.id
    assert created["text"] == text
    # FK traversal on POST response (note.user.username from shared DB)
    assert created["username"] == user.username

    get_response = client.get("/api/notes/")

    assert get_response.status_code == 200
    data = get_response.json()

    assert data["shared_db"]["user_count"] == expected_user_count
    assert data["tenant_db"]["note_count"] == 1
    note = data["tenant_db"]["notes"][0]
    assert note["text"] == text
    # FK traversal on GET response (note.user.username from shared DB)
    assert note["username"] == user.username


@pytest.mark.integration
def test_http_post_and_get_routes_to_tenant_db(client, allow_all_databases, isolated_tenant_dir, testapp_migrations):
    """
    Full HTTP round-trip: user signs up (post_save signal calls setup_tenant_db),
    then later admin runs migrate_tenant_dbs to re-migrate, then a logged-in
    user POSTs to create a note (middleware routes to tenant DB), then GETs
    to list notes (middleware routes again). Both requests use the standard
    request flow through TenantDatabaseMiddleware + router.
    """

    migrations_directory = testapp_migrations

    try:
        # Ensure default DB has auth and session tables
        call_command("migrate", verbosity=0)

        # Creating the user triggers the post_save signal which calls setup_user_db
        user1 = User.objects.create_user(id=5555, username="testuser", password="testpass")

        # User 1 creates a note and verifies their data
        _create_note_and_verify(client, user1, "User 1's note", expected_user_count=1)

        # Create second user - their DB is auto-created via post_save signal
        user2 = User.objects.create_user(id=7777, username="testuser2", password="testpass2")

        # User 2 creates their own note and verifies isolation
        _create_note_and_verify(client, user2, "User 2's note", expected_user_count=2)

        # User 1 GETs again - should still only see their own note, not user 2's
        client.force_login(user1)
        user1_notes = client.get("/api/notes/").json()

        assert user1_notes["tenant_db"]["note_count"] == 1
        assert user1_notes["tenant_db"]["notes"][0]["text"] == "User 1's note"
    finally:
        # Cleanup: remove generated migration files to avoid polluting the repo
        if os.path.exists(migrations_directory):
            shutil.rmtree(migrations_directory)
