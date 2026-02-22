from django.contrib import admin

from main.models import UserApproval, UserApprovalAuditLog, UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "country_prefix", "phone_number", "secondary_email", "updated_at")
    search_fields = (
        "user__username",
        "user__email",
        "secondary_email",
        "country_prefix",
        "phone_number",
    )


@admin.register(UserApproval)
class UserApprovalAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "reviewed_by", "reviewed_at", "updated_at")
    list_filter = ("status", "reviewed_at", "updated_at")
    search_fields = ("user__username", "user__email", "reviewed_by__username")


@admin.register(UserApprovalAuditLog)
class UserApprovalAuditLogAdmin(admin.ModelAdmin):
    list_display = ("target_user", "action", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("target_user__username", "target_user__email", "actor__username")
    readonly_fields = ("target_user", "actor", "action", "notes", "created_at")

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
