from rest_framework import serializers

from .models import Student, Teacher, User


class StudentAPISerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    status = serializers.CharField(source="user.status", read_only=True)

    class Meta:
        model = Student
        fields = [
            "id",
            "username",
            "full_name",
            "email",
            "status",
            "profile_picture_url",
            "bio",
            "date_of_birth",
            "grade_level",
        ]
        read_only_fields = ["id", "full_name", "email", "status"]


class TeacherAPISerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(source="user.full_name", read_only=True)
    email = serializers.EmailField(source="user.email", read_only=True)
    account_status = serializers.CharField(source="user.status", read_only=True)

    class Meta:
        model = Teacher
        fields = [
            "id",
            "full_name",
            "email",
            "account_status",
            "full_legal_name",
            "display_name",
            "phone_number",
            "country",
            "cv_url",
            "degree_certificate_url",
            "profile_picture_url",
            "headline",
            "years_of_experience",
            "bio",
            "subjects_expertise",
            "education_level_taught",
            "languages",
            "current_institution",
            "teaching_mode",
            "portfolio_url",
            "verification_status",
        ]
        read_only_fields = [
            "id",
            "full_name",
            "email",
            "account_status",
            "verification_status",
        ]