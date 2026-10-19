from rest_framework import serializers

from accounts.models import Student, Teacher
from .models import Course, Enrollment, Exam, Grade


class ExamAPISerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
    )
    teacher_name = serializers.CharField(
        source="course.teacher.display_name",
        read_only=True,
    )

    class Meta:
        model = Exam
        fields = [
            "id",
            "course",
            "course_title",
            "teacher_name",
            "title",
            "exam_date",
            "duration_minutes",
            "total_marks",
        ]
        read_only_fields = [
            "id",
            "course_title",
            "teacher_name",
        ]

    def validate_course(self, value):
        request = self.context.get("request")

        if request and request.user.role == "teacher":
            teacher = getattr(request.user, "teacher_profile", None)

            if teacher is None or value.teacher_id != teacher.id:
                raise serializers.ValidationError(
                    "You can only schedule exams for your own courses."
                )

        return value

    def validate_duration_minutes(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Exam duration must be at least one minute."
            )
        return value

    def validate_total_marks(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Total marks must be at least one."
            )
        return value


class GradeAPISerializer(serializers.ModelSerializer):
    exam_title = serializers.CharField(
        source="exam.title",
        read_only=True,
    )
    course_title = serializers.CharField(
        source="exam.course.title",
        read_only=True,
    )
    student_username = serializers.CharField(
        source="student.username",
        read_only=True,
    )
    student_name = serializers.CharField(
        source="student.user.full_name",
        read_only=True,
    )
    graded_by_email = serializers.EmailField(
        source="graded_by.email",
        read_only=True,
    )
    total_marks = serializers.IntegerField(
        source="exam.total_marks",
        read_only=True,
    )

    class Meta:
        model = Grade
        fields = [
            "id",
            "exam",
            "exam_title",
            "course_title",
            "total_marks",
            "student",
            "student_username",
            "student_name",
            "score",
            "grade_letter",
            "teacher_feedback",
            "graded_by",
            "graded_by_email",
            "graded_at",
        ]
        read_only_fields = [
            "id",
            "graded_by",
            "graded_at",
            "exam_title",
            "course_title",
            "total_marks",
            "student_username",
            "student_name",
            "graded_by_email",
        ]

    def validate(self, attrs):
        exam = attrs.get("exam", getattr(self.instance, "exam", None))
        student = attrs.get(
            "student",
            getattr(self.instance, "student", None),
        )
        score = attrs.get("score", getattr(self.instance, "score", None))

        if exam is not None and student is not None:
            is_enrolled = Enrollment.objects.filter(
                course=exam.course,
                student=student,
                status=Enrollment.Status.ACTIVE,
            ).exists()

            if not is_enrolled:
                raise serializers.ValidationError(
                    {
                        "student": (
                            "The student must be actively enrolled "
                            "in the exam's course."
                        )
                    }
                )

        if exam is not None and score is not None:
            if score < 0 or score > exam.total_marks:
                raise serializers.ValidationError(
                    {
                        "score": (
                            f"Score must be between 0 and "
                            f"{exam.total_marks}."
                        )
                    }
                )

        return attrs