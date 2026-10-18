from rest_framework import serializers


class ProfilePictureUploadSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(
        required=True,
        help_text="An image file to use as the profile picture.",
    )

    def validate_profile_picture(self, image):
        max_size = 5 * 1024 * 1024  # 5 MB

        if image.size > max_size:
            raise serializers.ValidationError(
                "The profile picture must not exceed 5 MB."
            )

        return image