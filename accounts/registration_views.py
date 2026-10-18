from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .serializers import StudentRegistrationSerializer


class StudentRegistrationView(generics.CreateAPIView):
    serializer_class = StudentRegistrationSerializer
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["Authentication"],
        summary="Register a student account",
        description=(
            "Creates a student account and its student profile. "
            "Public registration always assigns the student role. "
            "Passwords are validated and never returned."
        ),
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        return Response(
            {
                "message": "Student account created successfully.",
                "user": self.get_serializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )