from django.contrib import admin
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html


@login_required
def set_tenant(request):
    if not request.user.is_superuser:
        request.session.pop("admin_tenant_id", None)

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    if "tenant_id" in request.GET:
        request.session["admin_tenant_id"] = str(request.GET["tenant_id"])

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


@login_required
def unset_tenant(request):
    if not request.user.is_superuser:
        request.session.pop("admin_tenant_id", None)

        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))

    request.session.pop("admin_tenant_id", None)

    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


class SwitchTenantAdmin(admin.ModelAdmin):
    """
    ModelAdmin subclass that adds "Switch" / "Reset" buttons in the
    admin list view. Allows superusers to impersonate a tenant's DB context.

    This is designed for simple setups. For more complex setups with a separate
    tenant model, you may need a custom solution that maps users to their tenant.

    Usage:
        @admin.register(User)
        class UserAdmin(SwitchTenantAdmin, BaseUserAdmin):
            pass
    """

    def get_list_display(self, request):
        base = list(super().get_list_display(request))

        if request.user.is_superuser and "switch_tenant_button" not in base:
            base.append("switch_tenant_button")

        return base

    @admin.display(description="Switch Tenant")
    def switch_tenant_button(self, obj):
        set_url = reverse("dj_lite_tenant:set_tenant") + f"?tenant_id={obj.pk}"
        unset_url = reverse("dj_lite_tenant:unset_tenant")

        return format_html(
            '<a class="button" href="{}">Switch</a> <a class="button" href="{}">Reset</a>',
            set_url,
            unset_url,
        )
