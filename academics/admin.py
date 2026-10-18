from django.contrib import admin

from .models import Course, Enrollment


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "teacher",
        "visibility",
        "status",
        "course_limit",
    )
    list_filter = ("visibility", "status")
    search_fields = (
        "title",
        "description",
        "teacher__display_name",
        "teacher__user__email",
    )
    autocomplete_fields = ("teacher", "approved_by")


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ("course", "student", "status", "enrolled_at")
    list_filter = ("status", "enrolled_at")
    search_fields = (
        "course__title",
        "student__username",
        "student__user__email",
    )
    autocomplete_fields = ("course", "student")
    readonly_fields = ("enrolled_at",)