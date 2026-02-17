from django.contrib import admin
from .models import CustomUser, PasswordResetRequest


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "is_staff",
        "is_superuser",
        "is_authorized",
        "is_active",
        "date_joined",
    )
    search_fields = ("email",)
    list_filter = ("is_staff", "is_superuser", "is_authorized", "is_active", "date_joined")


@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ("user", "token", "created_at")
    search_fields = ("user__email", "token")
    list_filter = ("created_at",)
