from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import (
    OpenApiResponse,
    extend_schema,
    extend_schema_view,
)
from livekit import api
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
            "Returns sessions accessible to the authenticated user. "
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
            "Returns details for an accessible live session. "
            "Access depends on the authenticated user's role and course access."
        ),
        responses={
            200: LiveSessionSerializer,
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            404: OpenApiResponse(
                description="Session not found or not accessible."
            ),
        },
    ),
    create=extend_schema(
        tags=["Live Sessions"],
        summary="Schedule a live session",
        description=(
            "Creates a session for a course. Teachers can schedule sessions "
            "only for their own approved courses. Administrators can schedule "
            "sessions for any course. Provide course, starts_at, ends_at, "
            "and optionally tools_enabled. New sessions must start in the "
            "future and last longer than 15 minutes. Provider room and "
            "calculated deadline fields are read-only."
        ),
        request=LiveSessionSerializer,
        responses={
            201: LiveSessionSerializer,
            400: OpenApiResponse(
                description="Invalid or missing session data."
            ),
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            403: OpenApiResponse(
                description="The user cannot schedule this session."
            ),
        },
    ),
    update=extend_schema(
        tags=["Live Sessions"],
        summary="Replace live session details",
        description=(
            "Updates the writable fields of an accessible session. "
            "The request must include the required writable fields. "
            "Provider room and calculated deadline fields are read-only."
        ),
        request=LiveSessionSerializer,
        responses={
            200: LiveSessionSerializer,
            400: OpenApiResponse(
                description="Invalid session data."
            ),
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            404: OpenApiResponse(
                description="Session not found or not accessible."
            ),
        },
    ),
    partial_update=extend_schema(
        tags=["Live Sessions"],
        summary="Partially update a live session",
        description=(
            "Updates only the supplied writable fields of an accessible "
            "session. Session times are validated when provided."
        ),
        request=LiveSessionSerializer,
        responses={
            200: LiveSessionSerializer,
            400: OpenApiResponse(
                description="Invalid session data."
            ),
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            404: OpenApiResponse(
                description="Session not found or not accessible."
            ),
        },
    ),
    destroy=extend_schema(
        tags=["Live Sessions"],
        summary="Delete a live session",
        description=(
            "Deletes an accessible live session. Related attendance records "
            "are deleted according to the model's cascade relationship."
        ),
        responses={
            204: OpenApiResponse(
                description="Session deleted successfully."
            ),
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            404: OpenApiResponse(
                description="Session not found or not accessible."
            ),
        },
    ),
)
class LiveSessionViewSet(viewsets.ModelViewSet):
    """
    API for scheduling and managing live sessions.

    All endpoints require JWT authentication. Access is restricted according
    to the user's role and course access. LiveKit credentials remain on the
    backend; authorized participants receive short-lived join tokens.
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
            ).select_related(
                "course",
                "course__teacher",
            )

        if user.role == "student":
            return LiveSession.objects.filter(
                course__enrollments__student__user=user,
                course__enrollments__status="active",
            ).select_related(
                "course",
            ).distinct()

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
            raise PermissionDenied(
                "Your teacher profile was not found."
            )

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
        summary="Join a live video session",
        description=(
            "Generates a short-lived LiveKit participant token for an "
            "authenticated user who can access the session. Administrators "
            "can access all sessions, teachers can access sessions for their "
            "own courses, and students can access sessions for actively "
            "enrolled courses. The session must be within its joining window. "
            "The response contains the LiveKit server URL, room name, "
            "participant token, participant identity, and token lifetime. "
            "The API secret is never returned. The frontend must use the "
            "LiveKit client SDK to connect to the room."
        ),
        request=None,
        responses={
            200: OpenApiResponse(
                description=(
                    "LiveKit connection details and a participant token "
                    "valid for 10 minutes."
                )
            ),
            400: OpenApiResponse(
                description="The session has not started yet."
            ),
            401: OpenApiResponse(
                description="Authentication is required."
            ),
            403: OpenApiResponse(
                description="The joining deadline has passed."
            ),
            404: OpenApiResponse(
                description="Session not found or not accessible."
            ),
            503: OpenApiResponse(
                description=(
                    "LiveKit is not configured or a token could not be created."
                )
            ),
        },
    )
    @action(detail=True, methods=["post"])
    def join(self, request, pk=None):
        """
        Generate a short-lived LiveKit token for an authorized participant.
        """
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

        # Confirm the required LiveKit settings are configured.
        if not all(
            [
                settings.LIVEKIT_URL,
                settings.LIVEKIT_API_KEY,
                settings.LIVEKIT_API_SECRET,
            ]
        ):
            return Response(
                {
                    "detail": (
                        "Live video is not configured. "
                        "Please contact the administrator."
                    ),
                    "video_provider_configured": False,
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        # Use one consistent room name for every participant in this session.
        room_name = (
            live_session.provider_room_id
            or f"konnect-session-{live_session.pk}"
        )

        # Save the room name so future join requests use the same room.
        if not live_session.provider_room_id:
            live_session.provider_room_id = room_name
            live_session.save(update_fields=["provider_room_id"])

        # Avoid putting personal information into the room identity.
        participant_identity = f"user-{request.user.pk}"

        participant_name = (
            getattr(request.user, "full_name", "")
            or request.user.get_username()
        )

        try:
            participant_token = (
                api.AccessToken(
                    settings.LIVEKIT_API_KEY,
                    settings.LIVEKIT_API_SECRET,
                )
                .with_identity(participant_identity)
                .with_name(participant_name)
                .with_grants(
                    api.VideoGrants(
                        room_join=True,
                        room=room_name,
                        can_publish=True,
                        can_subscribe=True,
                        can_publish_data=True,
                    )
                )
                .with_ttl(timedelta(minutes=10))
                .to_jwt()
            )
        except Exception:
            # Do not return internal SDK errors or credentials to the client.
            return Response(
                {
                    "detail": (
                        "Unable to create a video access token. "
                        "Please try again later."
                    )
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                "server_url": settings.LIVEKIT_URL,
                "room_name": room_name,
                "participant_token": participant_token,
                "participant_identity": participant_identity,
                "token_expires_in": 600,
                "video_provider_configured": True,
            },
            status=status.HTTP_200_OK,
        )