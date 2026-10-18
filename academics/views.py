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

from .models import LiveSession
from .serializers import LiveSessionSerializer


@extend_schema_view(
    list=extend_schema(
        tags=["Live Sessions"],
        summary="List accessible live sessions",
        description=(
            "Returns live sessions the authenticated user is allowed to see. "
            "Administrators can see all sessions, teachers can see sessions "
            "for their own courses, and students can see sessions for courses "
            "in which they have an active enrollment."
        ),
        responses={200: LiveSessionSerializer(many=True)},
    ),
    retrieve=extend_schema(
        tags=["Live Sessions"],
        summary="Retrieve a live session",
        description=(
            "Returns details for one live session. The session must be "
            "accessible to the authenticated user's role and course access."
        ),
        responses={
            200: LiveSessionSerializer,
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    ),
    create=extend_schema(
        tags=["Live Sessions"],
        summary="Schedule a live session",
        description=(
            "Creates a live session for a course. Teachers may schedule sessions "
            "only for their own approved courses. Administrators may create "
            "sessions for any course. The request must include course, starts_at, "
            "and ends_at. Sessions must be scheduled in the future and last more "
            "than 15 minutes. Provider room and join-link fields are read-only."
        ),
        request=LiveSessionSerializer,
        responses={
            201: LiveSessionSerializer,
            400: OpenApiResponse(description="Invalid or missing session data."),
            401: OpenApiResponse(description="Authentication is required."),
            403: OpenApiResponse(description="The user cannot schedule this session."),
        },
    ),
    update=extend_schema(
        tags=["Live Sessions"],
        summary="Replace live session details",
        description=(
            "Updates a live session using the complete writable request fields. "
            "The user must have access to the session. Read-only provider and "
            "calculated deadline fields cannot be changed through this endpoint."
        ),
        request=LiveSessionSerializer,
        responses={
            200: LiveSessionSerializer,
            400: OpenApiResponse(description="Invalid session data."),
            401: OpenApiResponse(description="Authentication is required."),
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    ),
    partial_update=extend_schema(
        tags=["Live Sessions"],
        summary="Partially update a live session",
        description=(
            "Updates only the supplied writable fields of an accessible session. "
            "Session times are validated when provided."
        ),
        request=LiveSessionSerializer,
        responses={
            200: LiveSessionSerializer,
            400: OpenApiResponse(description="Invalid session data."),
            401: OpenApiResponse(description="Authentication is required."),
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    ),
    destroy=extend_schema(
        tags=["Live Sessions"],
        summary="Delete a live session",
        description=(
            "Deletes an accessible live session. Related attendance records "
            "are also deleted according to the model's cascade relationship."
        ),
        responses={
            204: OpenApiResponse(description="Session deleted successfully."),
            401: OpenApiResponse(description="Authentication is required."),
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    ),
)
class LiveSessionViewSet(viewsets.ModelViewSet):
    """
    API for scheduling, listing, retrieving, updating, and deleting live sessions.

    All endpoints require JWT authentication. Access is scoped by user role.
    Actual video joining remains unavailable until a provider is configured.
    """

    serializer_class = LiveSessionSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.role == "admin":
            return LiveSession.objects.select_related(
                "course",
                "course__teacher",
            ).all()

        if user.role == "teacher":
            return LiveSession.objects.filter(
                course__teacher__user=user
            ).select_related("course", "course__teacher")

        if user.role == "student":
            return LiveSession.objects.filter(
                course__enrollments__student__user=user,
                course__enrollments__status="active",
            ).select_related("course").distinct()

        return LiveSession.objects.none()

    def perform_create(self, serializer):
        user = self.request.user
        course = serializer.validated_data["course"]

        if user.role == "admin":
            serializer.save()
            return

        if user.role != "teacher":
            raise PermissionDenied(
                "Only teachers and administrators can schedule live sessions."
            )

        if not hasattr(user, "teacher_profile"):
            raise PermissionDenied("Your teacher profile was not found.")

        if course.teacher_id != user.teacher_profile.id:
            raise PermissionDenied(
                "You can only schedule sessions for your own courses."
            )

        if course.status != "approved":
            raise PermissionDenied(
                "Only approved courses can have live sessions scheduled."
            )

        serializer.save()

    @extend_schema(
        tags=["Live Sessions"],
        summary="Check live-session joining eligibility",
        description=(
            "Checks whether the session is within its permitted joining window. "
            "Joining is permitted from the scheduled start until 15 minutes "
            "after the start. This endpoint does not create a video connection. "
            "Until a video provider is configured, it returns HTTP 503 even "
            "when the timing checks pass."
        ),
        request=None,
        responses={
            503: OpenApiResponse(
                description=(
                    "Video joining is not configured. The response includes "
                    "video_provider_configured=false."
                )
            ),
            400: OpenApiResponse(description="The session has not started yet."),
            403: OpenApiResponse(description="The joining deadline has passed."),
            401: OpenApiResponse(description="Authentication is required."),
            404: OpenApiResponse(description="Session not found or not accessible."),
        },
    )
    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """Check session timing; does not establish a video connection."""
        live_session = self.get_object()
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

        return Response(
            {
                "detail": (
                    "The joining window is open, but video joining is unavailable "
                    "until a video provider is configured."
                ),
                "join_window_open": True,
                "video_provider_configured": False,
            },
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )