
from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from .models import Teacher, User


class TeacherRegistrationSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(
        write_only=True,
        trim_whitespace=False,
        validators=[validate_password],
    )
    full_legal_name = serializers.CharField(max_length=200)
    display_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    phone_number = serializers.CharField(
        max_length=30,
        required=False,
        allow_blank=True,
    )
    country = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
    )
    bio = serializers.CharField(
        required=False,
        allow_blank=True,
    )
    subjects_expertise = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    education_level_taught = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )
    years_of_experience = serializers.CharField(
        max_length=50,
        required=False,
        allow_blank=True,
    )
    languages = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    current_institution = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True,
    )

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )
        return value

    @transaction.atomic
    def create(self, validated_data):
        password = validated_data.pop("password")

        full_name = validated_data.pop("full_name")
        email = validated_data.pop("email")

        user = User.objects.create_user(
            email=email,
            password=password,
            full_name=full_name,
            role=User.Role.TEACHER,
            status=User.Status.ACTIVE,
            is_active=True,
        )

        teacher = Teacher.objects.create(
            user=user,
            verification_status=Teacher.VerificationStatus.PENDING,
            **validated_data,
        )

        return teacher

    def to_representation(self, instance):
        return {
            "id": str(instance.id),
            "user_id": str(instance.user_id),
            "full_name": instance.user.full_name,
            "email": instance.user.email,
            "role": instance.user.role,
            "status": instance.user.status,
            "full_legal_name": instance.full_legal_name,
            "display_name": instance.display_name,
            "verification_status": instance.verification_status,
        }
