
from django.db import transaction
from django.shortcuts import get_object_or_404

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse

from .admin_permissions import IsSuperAdmin
from .models import AdminProfile, Student, Teacher, User


class PendingUsersView(APIView):
    """
    List student and teacher accounts awaiting approval.
    Superadmin access only.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id="admin_list_pending_users",
        summary="List pending student and teacher accounts",
        description=(
            "Returns student and teacher accounts whose user status is "
            "pending. Requires an authenticated active superadmin."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "A list containing each pending user's ID, name, "
                    "email, role, account status, creation date, and "
                    "teacher verification status where applicable."
                )
            )
        },
        tags=["Superadmin Approvals"],
    )
    def get(self, request):
        users = User.objects.filter(
            role__in=[User.Role.STUDENT, User.Role.TEACHER],
            status=User.Status.PENDING,
        ).order_by("created_at")

        results = []

        for user in users:
            teacher_status = None

            if user.role == User.Role.TEACHER:
                teacher = Teacher.objects.filter(user=user).first()
                if teacher:
                    teacher_status = teacher.verification_status

            results.append(
                {
                    "id": str(user.id),
                    "full_name": user.full_name,
                    "email": user.email,
                    "role": user.role,
                    "status": user.status,
                    "is_active": user.is_active,
                    "created_at": user.created_at,
                    "teacher_verification_status": teacher_status,
                }
            )

        return Response(results, status=status.HTTP_200_OK)


class ApproveStudentView(APIView):
    """
    Approve a pending student account.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id="admin_approve_student",
        summary="Approve a student account",
        description=(
            "Activates a pending student account. The student must "
            "register first. On success, the account status becomes "
            "active and the student can obtain JWT tokens. "
            "Requires an authenticated active superadmin. "
            "No request body is required."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Student approved."),
            400: OpenApiResponse(
                description="The account is not pending or is not a student."
            ),
            404: OpenApiResponse(description="User not found."),
            403: OpenApiResponse(description="Superadmin access required."),
        },
        tags=["Superadmin Approvals"],
    )
    @transaction.atomic
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if user.role != User.Role.STUDENT:
            return Response(
                {"detail": "This endpoint only approves student accounts."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.status != User.Status.PENDING:
            return Response(
                {"detail": "Only pending student accounts can be approved."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not Student.objects.filter(user=user).exists():
            return Response(
                {"detail": "The student profile was not found."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.status = User.Status.ACTIVE
        user.is_active = True
        user.save(update_fields=["status", "is_active"])

        return Response(
            {
                "message": "Student account approved successfully.",
                "user_id": str(user.id),
                "role": user.role,
                "status": user.status,
                "is_active": user.is_active,
            },
            status=status.HTTP_200_OK,
        )


class RejectUserView(APIView):
    """
    Reject a pending student or teacher account.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id="admin_reject_user",
        summary="Reject a student or teacher account",
        description=(
            "Rejects a pending student or teacher account and keeps it "
            "inactive. If the user is a teacher, the teacher profile's "
            "verification status is also set to rejected. "
            "Requires an authenticated active superadmin. "
            "No request body is required."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Account rejected."),
            400: OpenApiResponse(
                description="The account cannot be rejected by this endpoint."
            ),
            404: OpenApiResponse(description="User not found."),
            403: OpenApiResponse(description="Superadmin access required."),
        },
        tags=["Superadmin Approvals"],
    )
    @transaction.atomic
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)

        if user.role not in [User.Role.STUDENT, User.Role.TEACHER]:
            return Response(
                {"detail": "Only student and teacher accounts can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if user.status != User.Status.PENDING:
            return Response(
                {"detail": "Only pending accounts can be rejected."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.status = User.Status.REJECTED
        user.is_active = False
        user.save(update_fields=["status", "is_active"])

        if user.role == User.Role.TEACHER:
            teacher = Teacher.objects.filter(user=user).first()

            if teacher:
                admin_profile, _ = AdminProfile.objects.get_or_create(
                    user=request.user
                )
                teacher.verification_status = (
                    Teacher.VerificationStatus.REJECTED
                )
                teacher.verified_by = admin_profile
                teacher.save(
                    update_fields=["verification_status", "verified_by"]
                )

        return Response(
            {
                "message": "Account rejected successfully.",
                "user_id": str(user.id),
                "role": user.role,
                "status": user.status,
                "is_active": user.is_active,
            },
            status=status.HTTP_200_OK,
        )


class PendingTeachersView(APIView):
    """
    List teacher profiles awaiting verification.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id="admin_list_pending_teachers",
        summary="List teachers awaiting verification",
        description=(
            "Returns teacher profiles with pending verification status, "
            "including the associated user account details. "
            "Requires an authenticated active superadmin."
        ),
        responses={
            200: OpenApiResponse(
                description=(
                    "A list of pending teacher profiles, including teacher "
                    "ID, user ID, name, email, verification status, and "
                    "account status."
                )
            )
        },
        tags=["Superadmin Approvals"],
    )
    def get(self, request):
        teachers = Teacher.objects.select_related("user").filter(
            verification_status=Teacher.VerificationStatus.PENDING
        ).order_by("user__created_at")

        results = [
            {
                "id": str(teacher.id),
                "user_id": str(teacher.user_id),
                "full_legal_name": teacher.full_legal_name,
                "display_name": teacher.display_name,
                "email": teacher.user.email,
                "country": teacher.country,
                "headline": teacher.headline,
                "verification_status": teacher.verification_status,
                "account_status": teacher.user.status,
                "is_active": teacher.user.is_active,
            }
            for teacher in teachers
        ]

        return Response(results, status=status.HTTP_200_OK)


class VerifyTeacherView(APIView):
    """
    Verify a teacher and activate their account.
    """

    permission_classes = [IsSuperAdmin]

    @extend_schema(
        operation_id="admin_verify_teacher",
        summary="Verify and activate a teacher",
        description=(
            "Marks a teacher profile as verified, records the verifying "
            "superadmin, and activates the associated user account. "
            "This allows the teacher to log in and use verified-teacher "
            "features. Requires an authenticated active superadmin. "
            "No request body is required."
        ),
        request=None,
        responses={
            200: OpenApiResponse(description="Teacher verified and activated."),
            400: OpenApiResponse(
                description="Teacher is already verified or has been rejected."
            ),
            404: OpenApiResponse(description="Teacher profile not found."),
            403: OpenApiResponse(description="Superadmin access required."),
        },
        tags=["Superadmin Approvals"],
    )
    @transaction.atomic
    def post(self, request, teacher_id):
        teacher = get_object_or_404(
            Teacher.objects.select_related("user"),
            pk=teacher_id,
        )

        if (
            teacher.verification_status
            == Teacher.VerificationStatus.VERIFIED
        ):
            return Response(
                {"detail": "This teacher is already verified."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            teacher.verification_status
            == Teacher.VerificationStatus.REJECTED
            or teacher.user.status == User.Status.REJECTED
        ):
            return Response(
                {
                    "detail": (
                        "A rejected teacher cannot be verified through "
                        "this endpoint."
                    )
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        admin_profile, _ = AdminProfile.objects.get_or_create(
            user=request.user
        )

        teacher.verification_status = Teacher.VerificationStatus.VERIFIED
        teacher.verified_by = admin_profile
        teacher.save(
            update_fields=["verification_status", "verified_by"]
        )

        teacher.user.status = User.Status.ACTIVE
        teacher.user.is_active = True
        teacher.user.save(update_fields=["status", "is_active"])

        return Response(
            {
                "message": "Teacher verified and activated successfully.",
                "teacher_id": str(teacher.id),
                "user_id": str(teacher.user_id),
                "email": teacher.user.email,
                "verification_status": teacher.verification_status,
                "account_status": teacher.user.status,
                "is_active": teacher.user.is_active,
            },
            status=status.HTTP_200_OK,
        )
