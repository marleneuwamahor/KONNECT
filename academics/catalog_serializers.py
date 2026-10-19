
from rest_framework import serializers

from accounts.models import Teacher

from .models import Course, Enrollment


class CourseAPISerializer(serializers.ModelSerializer):
    teacher = serializers.PrimaryKeyRelatedField(
        queryset=Teacher.objects.all(),
        required=False,
        help_text=(
            "Teacher UUID. Required for administrators creating a course. "
            "Teachers creating their own course should omit this field."
        ),
    )
    teacher_name = serializers.CharField(
        source="teacher.display_name",
        read_only=True,
    )

    class Meta:
        model = Course
        fields = [
            "id",
            "teacher",
            "teacher_name",
            "approved_by",
            "title",
            "description",
            "visibility",
            "course_limit",
            "status",
        ]
        read_only_fields = [
            "id",
            "approved_by",
            "status",
        ]

    def validate_teacher(self, value):
        """
        Ensure the selected teacher can be assigned a course.
        """
        request = self.context.get("request")

        if request and request.user.role == "admin":
            if (
                value.verification_status != Teacher.VerificationStatus.VERIFIED
                or value.user.status != "active"
                or not value.user.is_active
            ):
                raise serializers.ValidationError(
                    "Select a verified teacher with an active account."
                )

        return value


class EnrollmentAPISerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )
    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
    )

    class Meta:
        model = Enrollment
        fields = [
            "id",
            "course",
            "course_title",
            "student",
            "student_username",
            "status",
            "enrolled_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "enrolled_at",
        ]
