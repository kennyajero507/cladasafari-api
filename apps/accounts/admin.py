from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AdminUser, AuditLog, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'locked', 'description')
    search_fields = ('name',)


@admin.register(AdminUser)
class AdminUserAdmin(UserAdmin):
    ordering = ('name',)
    list_display = ('email', 'name', 'role', 'is_active', 'is_sample', 'last_login')
    list_filter = ('role', 'is_active', 'is_sample')
    search_fields = ('email', 'name')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Profile', {'fields': ('name', 'role', 'legacy_role', 'is_sample')}),
        ('Django admin access', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Dates', {'fields': ('last_login',)}),
    )
    add_fieldsets = ((None, {'classes': ('wide',), 'fields': ('email', 'name', 'role', 'password1', 'password2')}),)


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'actor_email', 'action', 'target_type', 'target_label')
    list_filter = ('action',)
    search_fields = ('actor_email', 'target_label')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
