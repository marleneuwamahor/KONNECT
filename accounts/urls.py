from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .profile_views import ProfilePictureUploadView

urlpatterns = [
    # Obtain an access token and a refresh token.
    path(
        "token/",
        TokenObtainPairView.as_view(),
        name="token_obtain_pair",
    ),

    # Obtain a new access token using a refresh token.
    path(
        "token/refresh/",
        TokenRefreshView.as_view(),
        name="token_refresh",
    ),

    # Upload the authenticated user's profile picture.
    path(
        "profile/picture/",
        ProfilePictureUploadView.as_view(),
        name="profile-picture-upload",
    ),
]