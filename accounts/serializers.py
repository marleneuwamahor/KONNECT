from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Student, User


class ProfilePictureUploadSerializer(serializers.Serializer):
    profile_picture = serializers.ImageField(
        required=True,
        help_text="An image file to use as the profile picture.",
    )

    def validate_profile_picture(self, image):
        max_size = 5 * 1024 * 1024

        if image.size > max_size:
            raise serializers.ValidationError(
                "The profile picture must not exceed 5 MB."
            )

        return image


class StudentRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    username = serializers.CharField(max_length=30)
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )
    date_of_birth = serializers.DateField(
        required=False,
        allow_null=True,
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    def validate_username(self, value):
        if Student.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError(
                "This username is already taken."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        raw_password = validated_data.pop("password")
        date_of_birth = validated_data.pop("date_of_birth", None)

        user = User.objects.create_user(
            email=validated_data["email"],
            raw_password=raw_password,
            role=User.Role.STUDENT,
            status=User.Status.PENDING,
            is_active=False,
            full_name=validated_data["full_name"],
        )

        Student.objects.create(
            user=user,
            username=validated_data["username"],
            date_of_birth=date_of_birth,
        )

        return user

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "full_name": instance.full_name,
            "email": instance.email,
            "role": instance.role,
            "status": instance.status,
            "username": instance.student_profile.username,
        }
