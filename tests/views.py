import json

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from tests.testapp.models import UserNote


@csrf_exempt
def notes_api(request):
    """
    Test view that exercises both databases:
    - Reads User from default (shared) DB via standard Django auth
    - POST: Creates UserNote in tenant DB via router (FK to shared DB)
    - GET: Reads UserNote from tenant DB, traverses FK to get user.username
    Returns JSON with counts and verifies cross-database FK traversal.
    """
    if request.method == "POST":
        data = json.loads(request.body)
        note = UserNote.objects.create(
            user=request.user,
            text=data.get("text", ""),
        )

        return JsonResponse(
            {
                "id": note.id,
                "user_id": note.user_id,
                "username": note.user.username,  # FK traversal to shared DB
                "text": note.text,
            },
            status=201,
        )

    user_count = User.objects.count()

    # Query notes and traverse FK to get usernames (tests ATTACH + cross-DB)
    notes = [
        {
            "id": n.id,
            "user_id": n.user_id,
            "username": n.user.username,  # FK traversal triggers query to shared DB
            "text": n.text,
        }
        for n in UserNote.objects.all()
    ]

    return JsonResponse(
        {
            "shared_db": {"user_count": user_count},
            "tenant_db": {"note_count": len(notes), "notes": notes},
        }
    )
