from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .profile_views import ProfilePictureUploadView
from .registration_views import StudentRegistrationView
from .api_views import StudentViewSet, TeacherViewSet
from .teacher_registration_views import TeacherRegistrationView

router = DefaultRouter()
router.register("students", StudentViewSet, basename="student")
router.register("teachers", TeacherViewSet, basename="teacher")


urlpatterns = [
    path("register/", StudentRegistrationView.as_view(), name="student-register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "profile/picture/",
        ProfilePictureUploadView.as_view(),
        name="profile-picture-upload",
    ),
path(
    "teachers/register/",
    TeacherRegistrationView.as_view(),
    name="teacher-register",
),
]

urlpatterns += router.urls