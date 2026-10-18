from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User, Student, Teacher, AdminProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "role", "status", "is_staff")
    list_filter = ("role", "status", "is_staff")
    search_fields = ("email", "full_name")
    readonly_fields = ("created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Personal information",
            {"fields": ("full_name", "role", "status", "profile_image", "phone", "bio")},
        ),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Management", {"fields": ("managed_by",)}),
        ("Dates", {"fields": ("last_login", "created_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "role", "password1", "password2"),
            },
        ),
    )


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("username", "user", "grade_level")
    search_fields = ("username", "user__email", "user__full_name")
    list_filter = ("grade_level",)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("display_name", "user", "verification_status", "country")
    search_fields = ("display_name", "full_legal_name", "user__email")
    list_filter = ("verification_status", "country")


@admin.register(AdminProfile)
class AdminProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "admin_level")
    search_fields = ("user__email", "user__full_name")
    list_filter = ("admin_level",)