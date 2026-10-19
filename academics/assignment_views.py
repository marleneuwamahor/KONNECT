from django.db.models import Q
from django.utils import timezone

from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from drf_spectacular.utils import extend_schema, extend_schema_view

from .assignment_serializers import (
    AssignmentAPISerializer,
    SubmissionAPISerializer,
    GradeSubmissionSerializer,
)
from .models import Assignment, Course, Enrollment, Submission


@extend_schema_view(
    list=extend_schema(
        tags=["Assignments"],
        summary="List assignments",
        description=(
            "Lists assignments visible to the authenticated user. "
            "Administrators can see all assignments. Teachers can see "
            "assignments belonging to their own courses. Students can see "
            "assignments for approved courses in which they have an active "
            "enrollment. Authentication is required."
        ),
    ),
    retrieve=extend_schema(
        tags=["Assignments"],
        summary="Retrieve an assignment",
        description=(
            "Returns assignment details only when the assignment is "
            "visible to the authenticated user."
        ),
    ),
    create=extend_schema(
        tags=["Assignments"],
        summary="Create an assignment",
        description=(
            "Creates a quiz or exercise. Active, verified teachers can "
            "create assignments only for their own courses. Administrators "
            "can create assignments for any existing course. Students "
            "cannot create assignments."
        ),
    ),
    update=extend_schema(
        tags=["Assignments"],
        summary="Replace an assignment",
        description=(
            "Replaces an assignment. Administrators and the teacher who "
            "owns the assignment's course are permitted. Teachers cannot "
            "move assignments into another teacher's course."
        ),
    ),
    partial_update=extend_schema(
        tags=["Assignments"],
        summary="Partially update an assignment",
        description=(
            "Updates selected assignment fields. Administrators and the "
            "teacher who owns the course can update the assignment."
        ),
    ),
    destroy=extend_schema(
        tags=["Assignments"],
        summary="Delete an assignment",
        description=(
            "Deletes an assignment. Administrators and the teacher who "
            "owns its course can delete it. Associated submissions are "
            "also deleted by the database relationship."
        ),
    ),
)
class AssignmentViewSet(viewsets.ModelViewSet):
    serializer_class = AssignmentAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Assignment.objects.select_related(
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

    def create(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "teacher"):
            raise PermissionDenied(
                "Only teachers and administrators can create assignments."
            )

        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        user = self.request.user

        if user.role == "admin":
            serializer.save()
            return

        teacher = getattr(user, "teacher_profile", None)

        if teacher is None:
            raise PermissionDenied("Your teacher profile was not found.")

        if (
            teacher.verification_status != "verified"
            or user.status != "active"
            or not user.is_active
        ):
            raise PermissionDenied(
                "Your teacher account must be active and verified "
                "before creating assignments."
            )

        course = serializer.validated_data["course"]

        if course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only create assignments for your own courses."
            )

        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user

        if user.role == "admin":
            serializer.save()
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only administrators and the course's teacher can update assignments."
            )

        teacher = getattr(user, "teacher_profile", None)

        if teacher is None:
            raise PermissionDenied("Your teacher profile was not found.")

        course = serializer.validated_data.get(
            "course",
            serializer.instance.course,
        )

        if course.teacher_id != teacher.id:
            raise PermissionDenied(
                "You can only assign work to your own courses."
            )

        serializer.save()

    def destroy(self, request, *args, **kwargs):
        if request.user.role not in ("admin", "teacher"):
            raise PermissionDenied(
                "Only teachers and administrators can delete assignments."
            )

        return super().destroy(request, *args, **kwargs)


@extend_schema_view(
    list=extend_schema(
        tags=["Submissions"],
        summary="List submissions",
        description=(
            "Administrators can view all submissions. Teachers can view "
            "submissions for their own courses. Students can view only "
            "their own submissions."
        ),
    ),
    retrieve=extend_schema(
        tags=["Submissions"],
        summary="Retrieve a submission",
        description=(
            "Returns a submission only if the authenticated user is its "
            "student, the teacher of its course, or an administrator."
        ),
    ),
    create=extend_schema(
        tags=["Submissions"],
        summary="Submit assignment answers",
        description=(
            "An enrolled student submits answers as a JSON object. The "
            "student identity is taken from the authenticated account, "
            "not from the request body. The course must be approved, "
            "the enrollment active, the due date not passed, and the "
            "student must not already have submitted this assignment."
        ),
        request=SubmissionAPISerializer,
        responses={201: SubmissionAPISerializer},
    ),
)
class SubmissionViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = SubmissionAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Submission.objects.select_related(
            "assignment",
            "assignment__course",
            "assignment__course__teacher",
            "student",
            "student__user",
        )

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(
                assignment__course__teacher__user=user
            )

        if user.role == "student":
            return queryset.filter(student__user=user)

        return queryset.none()

    def create(self, request, *args, **kwargs):
        if request.user.role != "student":
            raise PermissionDenied(
                "Only students can submit assignment answers."
            )

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        assignment = serializer.validated_data["assignment"]

        if assignment.course.status != Course.Status.APPROVED:
            raise ValidationError(
                {"assignment": "The course is not approved for students."}
            )

        student = getattr(request.user, "student_profile", None)

        if student is None:
            raise PermissionDenied("Your student profile was not found.")

        is_enrolled = Enrollment.objects.filter(
            course=assignment.course,
            student=student,
            status=Enrollment.Status.ACTIVE,
        ).exists()

        if not is_enrolled:
            raise PermissionDenied(
                "You must be actively enrolled in this course to submit work."
            )

        if timezone.now() > assignment.due_at:
            raise ValidationError(
                {"assignment": "The deadline for this assignment has passed."}
            )

        if Submission.objects.filter(
            assignment=assignment,
            student=student,
        ).exists():
            raise ValidationError(
                {
                    "assignment": (
                        "You have already submitted this assignment. "
                        "Multiple submissions are not currently supported."
                    )
                }
            )

        submission = serializer.save(student=student)

        output = self.get_serializer(submission)

        return Response(
            output.data,
            status=status.HTTP_201_CREATED,
        )

    @extend_schema(
        tags=["Submissions"],
        summary="Grade a submission",
        description=(
            "Allows the teacher who owns the course or an administrator "
            "to assign a score and optional feedback. The score must be "
            "between zero and the assignment's maximum score. Students "
            "cannot grade submissions."
        ),
        request=GradeSubmissionSerializer,
        responses={200: SubmissionAPISerializer},
    )
    @action(detail=True, methods=["patch"], url_path="grade")
    def grade(self, request, pk=None):
        submission = self.get_object()

        if request.user.role == "teacher":
            teacher = getattr(request.user, "teacher_profile", None)

            if (
                teacher is None
                or submission.assignment.course.teacher_id != teacher.id
            ):
                raise PermissionDenied(
                    "You can only grade submissions for your own courses."
                )

        elif request.user.role != "admin":
            raise PermissionDenied(
                "Only the course's teacher or an administrator can grade submissions."
            )

        grade_serializer = GradeSubmissionSerializer(data=request.data)
        grade_serializer.is_valid(raise_exception=True)

        score = grade_serializer.validated_data["score"]

        if score > submission.assignment.max_score:
            raise ValidationError(
                {
                    "score": (
                        f"The score cannot exceed "
                        f"{submission.assignment.max_score}."
                    )
                }
            )

        submission.score = score

        if "teacher_feedback" in grade_serializer.validated_data:
            submission.teacher_feedback = (
                grade_serializer.validated_data["teacher_feedback"]
            )

        submission.save(
            update_fields=["score", "teacher_feedback"]
        )

        output = self.get_serializer(submission)

        return Response(output.data, status=status.HTTP_200_OK)