from django.db.models import Q

from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .exam_grade_serializers import (
    ExamAPISerializer,
    GradeAPISerializer,
)
from .models import Course, Enrollment, Exam, Grade


def require_active_verified_teacher(user):
    """Return the teacher profile only for an active, verified teacher."""
    teacher = getattr(user, "teacher_profile", None)

    if (
        teacher is None
        or teacher.verification_status != "verified"
        or user.status != "active"
        or not user.is_active
    ):
        raise PermissionDenied(
            "Your teacher account must be active and verified."
        )

    return teacher


@extend_schema_view(
    list=extend_schema(
        tags=["Exams"],
        summary="List exams",
        description=(
            "Lists exams visible to the authenticated user. "
            "Administrators see all exams. Teachers see exams for their "
            "own courses. Students see exams for approved courses in "
            "which they have an active enrollment."
        ),
    ),
    retrieve=extend_schema(
        tags=["Exams"],
        summary="Retrieve an exam",
        description=(
            "Returns the details of an exam when it is visible to the "
            "authenticated user."
        ),
    ),
    create=extend_schema(
        tags=["Exams"],
        summary="Create an exam",
        description=(
            "Creates an exam using course, title, exam_date, "
            "duration_minutes, and total_marks. Administrators can "
            "create exams for any course. Active, verified teachers "
            "can create exams only for their own courses. Students "
            "cannot create exams."
        ),
    ),
    update=extend_schema(
        tags=["Exams"],
        summary="Replace an exam",
        description=(
            "Replaces an exam. Administrators can manage any exam; "
            "active, verified teachers can manage exams only for their "
            "own courses."
        ),
    ),
    partial_update=extend_schema(
        tags=["Exams"],
        summary="Partially update an exam",
        description=(
            "Updates selected exam fields. Administrators can update "
            "any exam; active, verified teachers can update exams for "
            "their own courses only."
        ),
    ),
    destroy=extend_schema(
        tags=["Exams"],
        summary="Delete an exam",
        description=(
            "Deletes an exam. Only administrators or the active, "
            "verified teacher who owns its course may delete it. "
            "Associated grades are deleted with the exam."
        ),
    ),
)
class ExamViewSet(viewsets.ModelViewSet):
    serializer_class = ExamAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Exam.objects.select_related(
            "course",
            "course__teacher",
            "course__teacher__user",
        )

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(course__teacher__user=user)

        if user.role == "student":
            return queryset.filter(
                course__status=Course.Status.APPROVED,
                course__enrollments__student__user=user,
                course__enrollments__status=Enrollment.Status.ACTIVE,
            ).distinct()

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role == "admin":
            serializer.save()
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only teachers and administrators can create exams."
            )

        teacher = require_active_verified_teacher(user)
        course = serializer.validated_data["course"]

        if course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only create exams for your own courses."
            )

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        if user.role == "admin":
            serializer.save()
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only teachers and administrators can update exams."
            )

        teacher = require_active_verified_teacher(user)
        course = serializer.validated_data.get(
            "course",
            serializer.instance.course,
        )

        if course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only manage exams for your own courses."
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "teacher"):
            raise PermissionDenied(
                "Only teachers and administrators can delete exams."
            )

        if request.user.role == "teacher":
            require_active_verified_teacher(request.user)

        return super().destroy(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        tags=["Grades"],
        summary="List exam grades",
        description=(
            "Administrators see all grades. Teachers see grades for "
            "exams in their own courses. Students see only their own "
            "grades. Results are restricted by the authenticated user's "
            "role and permissions."
        ),
    ),
    retrieve=extend_schema(
        tags=["Grades"],
        summary="Retrieve an exam grade",
        description=(
            "Returns a grade only if the authenticated user is its "
            "student, the teacher who owns the exam's course, or "
            "an administrator."
        ),
    ),
    create=extend_schema(
        tags=["Grades"],
        summary="Award an exam grade",
        description=(
            "Creates a grade using exam, student, score, and optional "
            "grade_letter and teacher_feedback. The graded_by field is "
            "set from the authenticated account. Only administrators "
            "or active, verified teachers who own the exam's course "
            "may award grades. The student must have an active "
            "enrollment in that course, the score cannot exceed "
            "the exam's total_marks, and each student can have only "
            "one grade per exam."
        ),
    ),
    update=extend_schema(
        tags=["Grades"],
        summary="Replace an exam grade",
        description=(
            "Replaces grade fields. Only administrators or the active, "
            "verified teacher who owns the exam's course can update it. "
            "The score and student enrollment are validated."
        ),
    ),
    partial_update=extend_schema(
        tags=["Grades"],
        summary="Partially update an exam grade",
        description=(
            "Updates selected grade fields. Only administrators or the "
            "active, verified teacher who owns the exam's course can "
            "update it. The score and student enrollment are validated."
        ),
    ),
    destroy=extend_schema(
        tags=["Grades"],
        summary="Delete an exam grade",
        description=(
            "Deletes a grade. Only administrators or the active, "
            "verified teacher who owns the exam's course may delete it."
        ),
    ),
)
class GradeViewSet(viewsets.ModelViewSet):
    serializer_class = GradeAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Grade.objects.select_related(
            "exam",
            "exam__course",
            "exam__course__teacher",
            "student",
            "student__user",
            "graded_by",
        )

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(
                exam__course__teacher__user=user
            )

        if user.role == "student":
            return queryset.filter(student__user=user)

        return queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "teacher"):
            raise PermissionDenied(
                "Only teachers and administrators can award grades."
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user
        exam = serializer.validated_data["exam"]

        if user.role == "admin":
            serializer.save(graded_by=user)
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only teachers and administrators can award grades."
            )

        teacher = require_active_verified_teacher(user)

        if exam.course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only grade exams for your own courses."
            )

        serializer.save(graded_by=user)

    def perform_update(self, serializer):
        user = self.request.user

        if user.role == "admin":
            serializer.save()
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only teachers and administrators can update grades."
            )

        teacher = require_active_verified_teacher(user)
        exam = serializer.validated_data.get(
            "exam",
            serializer.instance.exam,
        )

        if exam.course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only update grades for your own courses."
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "teacher"):
            raise PermissionDenied(
                "Only teachers and administrators can delete grades."
            )

        if request.user.role == "teacher":
            require_active_verified_teacher(request.user)

        return super().destroy(request, *args, **kwargs)