
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from .api_views import StudentViewSet, TeacherViewSet
from .approval_views import (
    ApproveStudentView,
    PendingTeachersView,
    PendingUsersView,
    RejectUserView,
    VerifyTeacherView,
)
from .profile_views import ProfilePictureUploadView
from .registration_views import StudentRegistrationView
from .teacher_registration_views import TeacherRegistrationView
from .token_serializers import AccountStatusTokenObtainPairSerializer


class AccountStatusTokenObtainPairView(TokenObtainPairView):
    """
    Authenticate users and issue JWT tokens only for approved active accounts.
    """

    serializer_class = AccountStatusTokenObtainPairSerializer


router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("teachers", TeacherViewSet, basename="teacher")


urlpatterns = [
    path(
        "register/",
        StudentRegistrationView.as_view(),
        name="student-register",
    ),
    path(
        "teachers/register/",
        TeacherRegistrationView.as_view(),
        name="teacher-register",
    ),
    path(
        "token/",
        AccountStatusTokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),
    path(
        "profile/picture/",
        ProfilePictureUploadView.as_view(),
        name="profile-picture-upload",
    ),

    # Superadmin account approval endpoints.
    path(
        "admin/pending-users/",
        PendingUsersView.as_view(),
        name="admin-pending-users",
    ),
    path(
        "admin/users/<uuid:user_id>/approve/",
        ApproveStudentView.as_view(),
        name="admin-approve-student",
    ),
    path(
        "admin/users/<uuid:user_id>/reject/",
        RejectUserView.as_view(),
        name="admin-reject-user",
    ),
    path(
        "admin/teachers/pending-verification/",
        PendingTeachersView.as_view(),
        name="admin-pending-teachers",
    ),
    path(
        "admin/teachers/<uuid:teacher_id>/verify/",
        VerifyTeacherView.as_view(),
        name="admin-verify-teacher",
    ),
]

urlpatterns += router.urls
