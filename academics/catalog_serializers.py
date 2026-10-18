from rest_framework import serializers

from .models import Course, Enrollment


class CourseAPISerializer(serializers.ModelSerializer):
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
        read_only_fields = ["id", "approved_by", "status"]


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
        read_only_fields = ["id", "status", "enrolled_at"]