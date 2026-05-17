from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from dj_lite_tenant.admin import SwitchTenantAdmin

from .models import Note


@admin.register(Note)
class NoteAdmin(admin.ModelAdmin):
    list_display = ("text", "created_at")


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(SwitchTenantAdmin, BaseUserAdmin):
    pass
