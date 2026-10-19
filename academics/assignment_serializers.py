from rest_framework import serializers

from .models import Assignment, Submission


class AssignmentAPISerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )

    class Meta:
        model = Assignment
        fields = [
            "id",
            "course",
            "course_title",
            "type",
            "title",
            "due_at",
            "max_score",
        ]
        read_only_fields = ["id", "course_title"]

    def validate_course(self, value):
        request = self.context.get("request")

        if request and request.user.role == "teacher":
            teacher = getattr(request.user, "teacher_profile", None)

            if teacher is None or value.teacher_id != teacher.id:
                raise serializers.ValidationError(
                    "You can only assign work to your own courses."
                )

        return value


class SubmissionAPISerializer(serializers.ModelSerializer):
    assignment_title = serializers.CharField(
        source="assignment.title",
        read_only=True,
    )
    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
    )
    course_title = serializers.CharField(
        source="assignment.course.title",
        read_only=True,
    )

    class Meta:
        model = Submission
        fields = [
            "id",
            "assignment",
            "assignment_title",
            "course_title",
            "student",
            "student_username",
            "answers",
            "score",
            "teacher_feedback",
            "submitted_at",
        ]
        read_only_fields = [
            "id",
            "student",
            "score",
            "teacher_feedback",
            "submitted_at",
        ]

    def validate_answers(self, value):
        if not isinstance(value, dict):
            raise serializers.ValidationError(
                "Answers must be a JSON object."
            )

        if not value:
            raise serializers.ValidationError(
                "Please provide at least one answer."
            )

        return value


class GradeSubmissionSerializer(serializers.Serializer):
    score = serializers.IntegerField(
        min_value=0,
        required=True,
        help_text="Awarded score, from zero up to the assignment's maximum score.",
    )
    teacher_feedback = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Optional feedback for the student.",
    )