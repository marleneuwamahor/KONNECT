from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView, TokenObtainPairView

from .api_views import StudentViewSet, TeacherViewSet
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
]

urlpatterns += router.urls