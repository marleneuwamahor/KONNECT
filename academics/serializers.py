from django.conf import settings
from django.utils import timezone
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from .models import Course, LiveSession


class LiveSessionSerializer(serializers.ModelSerializer):
    """
    Serializes live session data for the KONNECT frontend.

    Returns course information, session timing, attendance deadlines,
    and whether the joining window and LiveKit configuration are available.
    The frontend obtains its participant token from the join endpoint.
    """

    course_title = serializers.CharField(
        source="course.title",
        read_only=True,
        help_text="Title of the course associated with this session.",
    )

    course = serializers.PrimaryKeyRelatedField(
        queryset=Course.objects.all(),
        help_text="UUID of the course for this live session.",
    )

    join_window_open = serializers.SerializerMethodField(
        help_text=(
            "True when the current time is between the session start "
            "and its joining deadline, inclusive."
        )
    )

    video_provider_configured = serializers.SerializerMethodField(
        help_text=(
            "True when the required LiveKit URL, API key, and API secret "
            "are configured on the backend. This does not mean a participant "
            "is currently connected to the room."
        )
    )

    class Meta:
        model = LiveSession
        fields = [
            "id",
            "course",
            "course_title",
            "provider_room_id",
            "join_link",
            "tools_enabled",
            "starts_at",
            "ends_at",
            "join_deadline",
            "attendance_cutoff",
            "join_window_open",
            "video_provider_configured",
        ]

        read_only_fields = [
            "id",
            "provider_room_id",
            "join_link",
            "join_deadline",
            "attendance_cutoff",
            "join_window_open",
            "video_provider_configured",
        ]

        extra_kwargs = {
            "tools_enabled": {
                "help_text": (
                    "JSON list of session tools enabled for this session."
                )
            },
            "starts_at": {
                "help_text": (
                    "Scheduled start date and time, including timezone."
                )
            },
            "ends_at": {
                "help_text": (
                    "Scheduled end date and time, including timezone."
                )
            },
        }

    def validate(self, attrs):
        starts_at = attrs.get(
            "starts_at",
            getattr(self.instance, "starts_at", None),
        )
        ends_at = attrs.get(
            "ends_at",
            getattr(self.instance, "ends_at", None),
        )

        if starts_at and ends_at:
            if ends_at <= starts_at:
                raise serializers.ValidationError(
                    {
                        "ends_at": (
                            "The session end time must be after its start time."
                        )
                    }
                )

            duration = ends_at - starts_at

            if duration.total_seconds() <= 15 * 60:
                raise serializers.ValidationError(
                    {
                        "ends_at": (
                            "The session must last longer than 15 minutes "
                            "because attendance is evaluated 15 minutes "
                            "before it ends."
                        )
                    }
                )

            if self.instance is None and starts_at <= timezone.now():
                raise serializers.ValidationError(
                    {
                        "starts_at": (
                            "Schedule a new session for a future time."
                        )
                    }
                )

        return attrs

    @extend_schema_field(serializers.BooleanField())
    def get_join_window_open(self, obj):
        """Return whether the session's joining window is currently open."""
        now = timezone.now()
        return obj.starts_at <= now <= obj.join_deadline

    @extend_schema_field(serializers.BooleanField())
    def get_video_provider_configured(self, obj):
        """
        Return whether the backend has the required LiveKit configuration.
        """
        return bool(
            settings.LIVEKIT_URL
            and settings.LIVEKIT_API_KEY
            and settings.LIVEKIT_API_SECRET
        )