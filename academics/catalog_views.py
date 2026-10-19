
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, extend_schema_view

from .catalog_serializers import (
    CourseAPISerializer,
    EnrollmentAPISerializer,
)
from .models import Course, Enrollment


@extend_schema_view(
    list=extend_schema(
        tags=["Courses"],
        summary="List courses",
        description=(
            "Lists courses visible to the authenticated user. "
            "Administrators can view all courses, teachers can view "
            "their own courses, and students can view approved public "
            "courses and approved courses in which they are actively enrolled."
        ),
    ),
    retrieve=extend_schema(
        tags=["Courses"],
        summary="Retrieve a course",
        description=(
            "Returns one course if it is visible to the authenticated user."
        ),
    ),
    create=extend_schema(
        tags=["Courses"],
        summary="Create a course",
        description=(
            "Creates a course. Verified active teachers create courses "
            "for themselves and the course starts as a draft. Administrators "
            "must provide the UUID of an existing verified teacher with an "
            "active account. Students cannot create courses."
        ),
    ),
    update=extend_schema(
        tags=["Courses"],
        summary="Replace a course",
        description="Administrators can replace an existing course record.",
    ),
    partial_update=extend_schema(
        tags=["Courses"],
        summary="Partially update a course",
        description="Administrators can update selected course fields.",
    ),
    destroy=extend_schema(
        tags=["Courses"],
        summary="Delete a course",
        description="Administrators can delete a course.",
    ),
)
class CourseViewSet(viewsets.ModelViewSet):
    """
    Manage courses with role-based access.
    """

    serializer_class = CourseAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Course.objects.select_related(
            "teacher",
            "teacher__user",
            "approved_by",
        )

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(teacher__user=user)

        if user.role == "student":
            return queryset.filter(
                status=Course.Status.APPROVED
            ).filter(
                Q(visibility=Course.Visibility.PUBLIC)
                | Q(
                    enrollments__student__user=user,
                    enrollments__status=Enrollment.Status.ACTIVE,
                )
            ).distinct()

        return queryset.none()

    def perform_create(self, serializer):
        user = self.request.user

        if user.role == "admin":
            teacher = serializer.validated_data.get("teacher")

            if teacher is None:
                raise ValidationError(
                    {
                        "teacher": (
                            "Administrators must select an existing "
                            "verified teacher with an active account."
                        )
                    }
                )

            serializer.save(
                teacher=teacher,
                status=Course.Status.DRAFT,
                approved_by=None,
            )
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only verified teachers and administrators can create courses."
            )

        try:
            teacher = user.teacher_profile
        except user._meta.model.DoesNotExist:
            raise PermissionDenied("Your teacher profile was not found.")

        if (
            teacher.verification_status != "verified"
            or user.status != "active"
            or not user.is_active
        ):
            raise PermissionDenied(
                "Your teacher account must be active and verified "
                "before creating courses."
            )

        # Always assign the authenticated teacher. Ignore any teacher
        # UUID submitted by the client for a teacher-created course.
        serializer.save(
            teacher=teacher,
            status=Course.Status.DRAFT,
            approved_by=None,
        )

    def update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can update courses through this endpoint."
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can update courses through this endpoint."
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can delete courses."
            )
        return super().destroy(request, *args, **kwargs)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    Manage student course enrollments with role-based access.
    """

    serializer_class = EnrollmentAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Enrollment.objects.select_related(
            "course",
            "student",
            "student__user",
            "course__teacher",
        )

        if user.role == "admin":
            return queryset

        if user.role == "student":
            return queryset.filter(student__user=user)

        if user.role == "teacher":
            return queryset.filter(course__teacher__user=user)

        return queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("student", "admin"):
            raise PermissionDenied(
                "Only students and administrators can create enrollments."
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        course = serializer.validated_data["course"]
        student = serializer.validated_data["student"]

        if request.user.role == "student":
            try:
                own_profile = request.user.student_profile
            except request.user._meta.model.DoesNotExist:
                raise PermissionDenied(
                    "Your student profile was not found."
                )

            if student.id != own_profile.id:
                raise PermissionDenied(
                    "Students can only enroll themselves."
                )

        if course.status != Course.Status.APPROVED:
            raise ValidationError(
                {"course": "You can only enroll in approved courses."}
            )

        if course.visibility != Course.Visibility.PUBLIC:
            raise ValidationError(
                {"course": "This course is not open for public enrollment."}
            )

        existing_enrollment = Enrollment.objects.filter(
            course=course,
            student=student,
        ).exists()

        if existing_enrollment:
            raise ValidationError(
                {"detail": "This student is already enrolled in the course."}
            )

        if course.course_limit > 0:
            active_count = Enrollment.objects.filter(
                course=course,
                status=Enrollment.Status.ACTIVE,
            ).count()

            if active_count >= course.course_limit:
                raise ValidationError(
                    {"course": "This course has reached its enrollment limit."}
                )

        enrollment = serializer.save(student=student)
        output = self.get_serializer(enrollment)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can update enrollment records."
            )
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can update enrollment records."
            )
        return super().partial_update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        if request.user.role != "admin":
            raise PermissionDenied(
                "Only administrators can delete enrollment records."
            )
        return super().destroy(request, *args, **kwargs)
