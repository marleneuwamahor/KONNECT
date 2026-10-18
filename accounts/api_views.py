from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ReadOnlyModelViewSet

from .api_serializers import StudentAPISerializer, TeacherAPISerializer
from .models import Student, Teacher


class StudentViewSet(ReadOnlyModelViewSet):
    """
    Administrators can view all students.
    Students can view their own profile.
    Teachers can view students enrolled in their courses.
    """

    serializer_class = StudentAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Student.objects.select_related("user")

        if user.role == "admin":
            return queryset

        if user.role == "student":
            return queryset.filter(user=user)

        if user.role == "teacher":
            return queryset.filter(
                enrollments__course__teacher__user=user
            ).distinct()

        return queryset.none()


class TeacherViewSet(ReadOnlyModelViewSet):
    """
    Administrators can view all teachers.
    Teachers can view their own profile.
    Students can view verified teachers with active accounts.
    """

    serializer_class = TeacherAPISerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        queryset = Teacher.objects.select_related("user", "verified_by")

        if user.role == "admin":
            return queryset

        if user.role == "teacher":
            return queryset.filter(user=user)

        if user.role == "student":
            return queryset.filter(
                verification_status=Teacher.VerificationStatus.VERIFIED,
                user__status="active",
                user__is_active=True,
            )

        return queryset.none()