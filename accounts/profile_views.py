from django.core.exceptions import ObjectDoesNotExist
from drf_spectacular.utils import extend_schema, OpenApiResponse
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AdminProfile, Student, Teacher, User
from .serializers import ProfilePictureUploadSerializer


class ProfilePictureUploadView(APIView):
    """
    Upload or replace the authenticated user's profile picture.

    The image is saved to the User record and, when applicable,
    the associated Student, Teacher, or AdminProfile record.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        operation_id="upload_my_profile_picture",
        tags=["Profiles"],
        summary="Upload my profile picture",
        description=(
            "Uploads or replaces the authenticated user's profile picture. "
            "Send multipart/form-data with a 'profile_picture' image file. "
            "Maximum file size is 5 MB. The API updates the user's picture "
            "and the matching Student, Teacher, or AdminProfile picture. "
            "Authentication is required; users cannot upload pictures "
            "for other accounts."
        ),
        request=ProfilePictureUploadSerializer,
        responses={
            200: OpenApiResponse(
                description=(
                    "Profile picture uploaded successfully. Returns the "
                    "user picture URL and the role-specific profile URL "
                    "when a matching profile exists."
                )
            ),
            400: OpenApiResponse(
                description="Missing, invalid, or oversized image."
            ),
            401: OpenApiResponse(
                description="Authentication credentials were not provided "
                "or are invalid."
            ),
        },
    )
    def post(self, request):
        serializer = ProfilePictureUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        image = serializer.validated_data["profile_picture"]
        user = request.user

        # Save the general user profile picture.
        user.profile_image = image
        user.save(update_fields=["profile_image"])

        # Also update the profile associated with the user's role.
        role_profile_url = None

        if user.role == User.Role.STUDENT:
            try:
                profile = user.student_profile
            except ObjectDoesNotExist:
                profile = None

            if profile:
                profile.profile_picture_url = image
                profile.save(update_fields=["profile_picture_url"])
                role_profile_url = request.build_absolute_uri(
                    profile.profile_picture_url.url
                )

        elif user.role == User.Role.TEACHER:
            try:
                profile = user.teacher_profile
            except ObjectDoesNotExist:
                profile = None

            if profile:
                profile.profile_picture_url = image
                profile.save(update_fields=["profile_picture_url"])
                role_profile_url = request.build_absolute_uri(
                    profile.profile_picture_url.url
                )

        elif user.role == User.Role.ADMIN:
            profile, _ = AdminProfile.objects.get_or_create(user=user)
            profile.profile_picture_url = image
            profile.save(update_fields=["profile_picture_url"])
            role_profile_url = request.build_absolute_uri(
                profile.profile_picture_url.url
            )

        return Response(
            {
                "success": True,
                "message": "Profile picture uploaded successfully.",
                "profile_picture_url": request.build_absolute_uri(
                    user.profile_image.url
                ),
                "role_profile_picture_url": role_profile_url,
            },
            status=status.HTTP_200_OK,
        )
