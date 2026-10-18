from django.contrib import admin

from .models import Course, Enrollment, LiveSession, Attendance


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


@admin.register(LiveSession)
class LiveSessionAdmin(admin.ModelAdmin):
    list_display = (
        "course",
        "starts_at",
        "ends_at",
        "join_deadline",
        "attendance_cutoff",
    )
    list_filter = ("starts_at", "ends_at")
    search_fields = ("course__title", "provider_room_id")
    readonly_fields = ("join_deadline", "attendance_cutoff")


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "live_session",
        "status",
        "joined_at",
        "left_at",
        "auto_marked",
    )
    list_filter = ("status", "auto_marked")
    search_fields = (
        "student__username",
        "student__user__email",
        "live_session__course__title",
    )
    readonly_fields = ("marked_at",)