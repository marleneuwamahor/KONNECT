
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .teacher_registration_serializers import TeacherRegistrationSerializer


class TeacherRegistrationView(generics.CreateAPIView):
    serializer_class = TeacherRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Authentication"],
        summary="Register a teacher account",
        description=(
            "Creates a teacher account and profile. "
            "The teacher role is assigned automatically. "
            "New teacher accounts require administrator verification."
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        teacher = serializer.save()

        return Response(
            {
                "message": (
                    "Teacher account created successfully. "
                    "Your account is pending administrator verification."
                ),
                "teacher": self.get_serializer(teacher).data,
            },
            status=status.HTTP_201_CREATED,
        )
