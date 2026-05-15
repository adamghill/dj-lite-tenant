from django.urls import path

from django_sqlite_tenant.admin import set_user, unset_user

app_name = "django_sqlite_tenant"

urlpatterns = [
    path("tenant/set-user/", set_user, name="set_user"),
    path("tenant/unset-user/", unset_user, name="unset_user"),
]
