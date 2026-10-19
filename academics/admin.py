from django.contrib import admin

from .models import (
    Course,
    Enrollment,
    LiveSession,
    Attendance,
    Assignment,
    Submission,
)
from .models import (
    Course,
    Enrollment,
    LiveSession,
    Attendance,
    Assignment,
    Submission,
    Exam,
    Grade,
)


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


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "type",
        "due_at",
        "max_score",
    )
    list_filter = ("type", "course", "due_at")
    search_fields = (
        "title",
        "course__title",
        "course__teacher__user__email",
    )
    autocomplete_fields = ("course",)
    ordering = ("due_at",)


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = (
        "assignment",
        "student",
        "score",
        "submitted_at",
    )
    list_filter = ("assignment", "submitted_at")
    search_fields = (
        "assignment__title",
        "student__username",
        "student__user__email",
        "student__user__full_name",
    )
    autocomplete_fields = ("assignment", "student")
    readonly_fields = ("submitted_at",)

@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "exam_date",
        "duration_minutes",
        "total_marks",
    )
    list_filter = ("exam_date", "course")
    search_fields = ("title", "course__title")
    autocomplete_fields = ("course",)
    ordering = ("exam_date",)


@admin.register(Grade)
class GradeAdmin(admin.ModelAdmin):
    list_display = (
        "exam",
        "student",
        "score",
        "grade_letter",
        "graded_by",
        "graded_at",
    )
    list_filter = ("exam", "grade_letter", "graded_at")
    search_fields = (
        "exam__title",
        "student__username",
        "student__user__email",
        "graded_by__email",
    )
    autocomplete_fields = ("exam", "student", "graded_by")
    readonly_fields = ("graded_at",)