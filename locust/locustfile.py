"""
Locust load-test for dj-lite-tenant example app.

Targets the example Django project (HTML form-based views).

Prerequisites:
  1. Run `just locust-setup` to create test users and seed their tenant DBs.
  2. Start the example app: `just serve-gunicorn` (or `just serve` for single-threaded)
  3. Run Locust: `just locust` (or `just locust --headless --users 10 --run-time 60s`)

Two user classes are defined:

  TenantReadUser  — logs in once, then repeatedly GETs the notes list page.
  TenantWriteUser — logs in once, alternates between adding notes and reading the list.

Adjust NUM_USERS in setup.py to match the --users flag you pass to Locust.
"""

import random

from locust import HttpUser, between, task

NUM_USERS = 10
USER_PASSWORD = "locustpass123"


class _BaseUser(HttpUser):
    """Shared login logic for all user classes."""

    abstract = True
    wait_time = between(0.5, 2)

    def on_start(self):
        """Log in via the Django session-based login view."""

        self.user_number = random.randint(1, NUM_USERS)
        username = f"locustuser{self.user_number}"

        resp = self.client.get("/accounts/login/")
        csrftoken = resp.cookies.get("csrftoken", "")

        login_resp = self.client.post(
            "/accounts/login/",
            data={
                "username": username,
                "password": USER_PASSWORD,
                "csrfmiddlewaretoken": csrftoken,
            },
            headers={"Referer": f"{self.host}/accounts/login/"},
        )

        if login_resp.status_code not in (200, 302):
            raise RuntimeError(
                f"Login failed for {username} (status {login_resp.status_code}). Run `just locust-setup` first."
            )


class TenantReadUser(_BaseUser):
    """Repeatedly reads the notes list — exercises the tenant DB read path."""

    weight = 3

    @task
    def list_notes(self):
        self.client.get("/", name="GET /notes/list")


class TenantWriteUser(_BaseUser):
    """Alternates between writing and reading notes — exercises write + read paths."""

    weight = 1

    @task(3)
    def list_notes(self):
        self.client.get("/", name="GET /notes/list")

    @task(1)
    def add_note(self):
        resp = self.client.get("/notes/add/", name="GET /notes/add")
        csrftoken = resp.cookies.get("csrftoken", "")

        self.client.post(
            "/notes/add/",
            data={
                "text": f"Load test note from user{self.user_number} #{random.randint(1, 9999)}",
                "csrfmiddlewaretoken": csrftoken,
            },
            headers={"Referer": f"{self.host}/notes/add/"},
            name="POST /notes/add",
        )
