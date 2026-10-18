from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import Attendance, Enrollment, LiveSession
from .attendance_serializers import AttendanceSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Attendance"],
        summary="List attendance records",
        description=(
            "Lists attendance records visible to the authenticated user. "
            "Students can view their own records, teachers can view records "
            "for their own courses, and administrators can view all records."
        ),
        responses={200: AttendanceSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Attendance"],
        summary="Retrieve an attendance record",
        description="Returns one attendance record if the user is authorized to see it.",
        responses={
            200: AttendanceSerializer,
            404: OpenApiResponse(description="Record not found or not accessible."),
        },
    ),
)
class AttendanceViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Read-only API for attendance records.

    Attendance changes are performed through the join, leave, and cutoff
    actions rather than direct edits to attendance fields.
    """

    serializer_class = AttendanceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Attendance.objects.select_related(
            "student",
            "student__user",
            "live_session",
            "live_session__course",
            "live_session__course__teacher",
        )

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(
                live_session__course__teacher__user=user
            )

        if user.role == "student":
            return queryset.filter(student__user=user)

        return queryset.none()

    def _get_student_profile(self, user):
        if user.role != "student":
            raise PermissionDenied("Only students can use this action.")

        try:
            return user.student_profile
        except user.__class__.student_profile.RelatedObjectDoesNotExist:
            raise PermissionDenied("Your student profile was not found.")

    def _get_enrolled_student(self, user, live_session):
        student = self._get_student_profile(user)

        is_enrolled = Enrollment.objects.filter(
            course=live_session.course,
            student=student,
            status=Enrollment.Status.ACTIVE,
        ).exists()

        if not is_enrolled:
            raise PermissionDenied(
                "You must be actively enrolled in this course."
            )

        return student

    @extend_schema(
        tags=["Attendance"],
        summary="Register a student's session join",
        description=(
            "Records the authenticated student's join time for a live session. "
            "The student must be actively enrolled and must join between the "
            "scheduled start and the 15-minute joining deadline. Repeated join "
            "requests do not create duplicate records. This endpoint records an "
            "API event; until a trusted video-provider integration exists, it "
            "does not verify actual presence in a video room."
        ),
        request=None,
        responses={
            200: AttendanceSerializer,
            201: AttendanceSerializer,
            400: OpenApiResponse(description="The session has not started or attendance is already finalized."),
            403: OpenApiResponse(description="The user is not enrolled or the joining deadline passed."),
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="sessions/(?P<session_id>[^/.]+)/join",
    )
    def join_session(self, request, session_id=None):
        try:
            live_session = LiveSession.objects.select_related("course").get(
                pk=session_id
            )
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        student = self._get_enrolled_student(request.user, live_session)
        now = timezone.now()

        if now < live_session.starts_at:
            return Response(
                {"detail": "This session has not started yet."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if now > live_session.join_deadline:
            return Response(
                {"detail": "The joining deadline has passed."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if now >= live_session.attendance_cutoff:
            return Response(
                {"detail": "The attendance cutoff has already passed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            attendance, created = Attendance.objects.get_or_create(
                live_session=live_session,
                student=student,
                defaults={
                    "joined_at": now,
                    "status": Attendance.Status.ABSENT,
                },
            )

            if not created:
                if attendance.marked_at is not None:
                    return Response(
                        {"detail": "Attendance has already been finalized."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                if attendance.left_at is not None:
                    return Response(
                        {"detail": "A recorded departure cannot be overwritten by a join request."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        return Response(
            AttendanceSerializer(attendance).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @extend_schema(
        tags=["Attendance"],
        summary="Register a student's session departure",
        description=(
            "Records the authenticated student's departure time. The student "
            "must have a previous attendance record for this session. If the "
            "student leaves before the attendance cutoff, the cutoff process "
            "will mark the record absent. Leaving after the cutoff does not "
            "change an already finalized result."
        ),
        request=None,
        responses={
            200: AttendanceSerializer,
            400: OpenApiResponse(description="No join record exists or attendance is already finalized."),
            403: OpenApiResponse(description="The user is not enrolled in the course."),
            404: OpenApiResponse(description="Session or attendance record not found."),
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="sessions/(?P<session_id>[^/.]+)/leave",
    )
    def leave_session(self, request, session_id=None):
        try:
            live_session = LiveSession.objects.get(pk=session_id)
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        student = self._get_enrolled_student(request.user, live_session)

        try:
            attendance = Attendance.objects.get(
                live_session=live_session,
                student=student,
            )
        except Attendance.DoesNotExist:
            return Response(
                {"detail": "You have no recorded join for this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if attendance.marked_at is not None:
            return Response(
                {"detail": "Attendance has already been finalized."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if attendance.left_at is None:
            attendance.left_at = timezone.now()
            attendance.save(update_fields=["left_at"])

        return Response(AttendanceSerializer(attendance).data)

    @extend_schema(
        tags=["Attendance"],
        summary="Finalize attendance at the session cutoff",
        description=(
            "Allows a teacher who owns the course or an administrator to "
            "finalize attendance once the cutoff time has been reached. "
            "Students are marked present if they joined and had not left "
            "before the cutoff; otherwise they are marked absent. Repeated "
            "requests do not overwrite finalized records. This endpoint "
            "supports manual triggering until scheduled automation is added."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description="Attendance finalization summary.",
                response={
                    "type": "object",
                    "properties": {
                        "detail": {"type": "string"},
                        "finalized_count": {"type": "integer"},
                    },
                },
            ),
            400: OpenApiResponse(description="The attendance cutoff has not been reached."),
            403: OpenApiResponse(description="Only the course teacher or an administrator can finalize attendance."),
            404: OpenApiResponse(description="Session not found."),
        },
    )
    @action(
        detail=False,
        methods=["post"],
        url_path="sessions/(?P<session_id>[^/.]+)/finalize",
    )
    def finalize_session(self, request, session_id=None):
        try:
            live_session = LiveSession.objects.select_related(
                "course",
                "course__teacher",
            ).get(pk=session_id)
        except LiveSession.DoesNotExist:
            return Response(
                {"detail": "Live session not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        user = request.user

        if user.role != "admin":
            if (
                user.role != "teacher"
                or not hasattr(user, "teacher_profile")
                or live_session.course.teacher_id != user.teacher_profile.id
            ):
                raise PermissionDenied(
                    "Only the course teacher or an administrator can finalize attendance."
                )

        now = timezone.now()

        if now < live_session.attendance_cutoff:
            return Response(
                {
                    "detail": "The attendance cutoff has not been reached.",
                    "attendance_cutoff": live_session.attendance_cutoff,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        finalized_count = 0

        with transaction.atomic():
            records = Attendance.objects.select_for_update().filter(
                live_session=live_session,
                marked_at__isnull=True,
            )

            for attendance in records:
                stayed_until_cutoff = (
                    attendance.joined_at is not None
                    and attendance.joined_at <= live_session.attendance_cutoff
                    and (
                        attendance.left_at is None
                        or attendance.left_at >= live_session.attendance_cutoff
                    )
                )

                attendance.status = (
                    Attendance.Status.PRESENT
                    if stayed_until_cutoff
                    else Attendance.Status.ABSENT
                )
                attendance.auto_marked = True
                attendance.marked_at = now
                attendance.save(
                    update_fields=["status", "auto_marked", "marked_at"]
                )
                finalized_count += 1

        return Response(
            {
                "detail": "Attendance finalization completed.",
                "finalized_count": finalized_count,
            }
        )