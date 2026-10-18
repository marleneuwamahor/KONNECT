from rest_framework import serializers
from drf_spectacular.utils import extend_schema_field

from .models import Attendance


class AttendanceSerializer(serializers.ModelSerializer):
    """
    Read-only attendance details for the KONNECT frontend.
    """

    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
        help_text="Username or student identifier.",
    )

    student_name = serializers.CharField(
        source="student.user.full_name",
        read_only=True,
        help_text="Full name of the student.",
    )

    session_course_title = serializers.CharField(
        source="live_session.course.title",
        read_only=True,
        help_text="Title of the course associated with this session.",
    )

    class Meta:
        model = Attendance
        fields = [
            "id",
            "live_session",
            "session_course_title",
            "student",
            "student_username",
            "student_name",
            "status",
            "joined_at",
            "left_at",
            "auto_marked",
            "marked_at",
        ]
        read_only_fields = fields