from django.urls import path

from tests import views

urlpatterns = [
    path("api/notes/", views.notes_api, name="notes_api"),
]
