from django.contrib import admin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.utils.html import format_html


def set_user(request):
    if not request.user.is_superuser:
        request.session.pop("admin_user_id", None)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    if "user_id" in request.GET:
        request.session["admin_user_id"] = int(request.GET["user_id"])
        request.session.modified = True
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


def unset_user(request):
    if not request.user.is_superuser:
        request.session.pop("admin_user_id", None)
        return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))
    request.session.pop("admin_user_id", None)
    request.session.modified = True
    return HttpResponseRedirect(request.META.get("HTTP_REFERER", "/"))


class SwitchUserAdminMixin(admin.ModelAdmin):
    """
    Mixin for the User ModelAdmin that adds a "Switch User" button in the
    admin list view. Allows superusers to impersonate a user's DB context.

    Usage:
        @admin.register(User)
        class UserAdmin(SwitchUserAdminMixin, BaseUserAdmin):
            pass
    """

    def get_list_display(self, request):
        base = list(super().get_list_display(request))
        if "switch_user_button" not in base:
            base.append("switch_user_button")
        return base

    @admin.display(description="Switch User")
    def switch_user_button(self, obj):
        set_url = reverse("django_sqlite_tenant:set_user") + f"?user_id={obj.id}"
        unset_url = reverse("django_sqlite_tenant:unset_user")
        return format_html(
            '<a class="button" href="{}">Switch</a> '
            '<a class="button" href="{}">Reset</a>',
            set_url,
            unset_url,
        )
