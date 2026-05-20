# ruff: noqa: T201
"""
Pre-flight setup script for the Locust load test.

Creates NUM_USERS test users in the example app's shared DB and provisions
their per-tenant SQLite databases so the first Locust request is not slowed
down by DB migration.

Run from the repo root BEFORE starting Locust:

    python locust/setup.py

The script uses Django's management API directly, so the example app's
settings module must be importable (i.e. run from the repo root with the
virtual environment active).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "example"))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")

import django

django.setup()

from django.contrib.auth.models import User  # noqa: E402
from django.core.management import call_command  # noqa: E402

NUM_USERS = 10
PASSWORD = "locustpass123"


def main():
    call_command("migrate", verbosity=1)

    print(f"Creating {NUM_USERS} test users ...")

    for i in range(1, NUM_USERS + 1):
        username = f"locustuser{i}"

        if User.objects.filter(username=username).exists():
            print(f"  {username} already exists, skipping")
        else:
            User.objects.create_user(username=username, password=PASSWORD)
            print(f"  Created {username}")

    print("Done. Each user's tenant DB has been provisioned via post_save signal.")


if __name__ == "__main__":
    main()
