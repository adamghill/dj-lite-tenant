from django.urls import path

from dj_lite_tenant.admin import set_tenant, unset_tenant

app_name = "dj_lite_tenant"

urlpatterns = [
    path("set-tenant/", set_tenant, name="set_tenant"),
    path("unset-tenant/", unset_tenant, name="unset_tenant"),
]
