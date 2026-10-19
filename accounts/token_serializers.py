from django.contrib.auth import get_user_model
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


User = get_user_model()


class AccountStatusTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Issue JWT tokens only to users whose accounts are active and approved.
    """

    def validate(self, attrs):
        email = attrs.get(User.USERNAME_FIELD)
        password = attrs.get("password")

        # Look up the account and verify the password directly so we can
        # return the correct approval status for inactive accounts.
        try:
            user = User.objects.get(**{User.USERNAME_FIELD: email})
        except User.DoesNotExist:
            raise AuthenticationFailed(
                "Unable to log in with the provided credentials.",
                code="invalid_credentials",
            )

        if not user.check_password(password):
            raise AuthenticationFailed(
                "Unable to log in with the provided credentials.",
                code="invalid_credentials",
            )

        if user.status == User.Status.PENDING:
            raise AuthenticationFailed(
                "Your account is awaiting administrator approval.",
                code="account_pending",
            )

        if user.status == User.Status.REJECTED:
            raise AuthenticationFailed(
                "Your account registration was rejected. Please contact the administrator.",
                code="account_rejected",
            )

        if user.status == User.Status.SUSPENDED:
            raise AuthenticationFailed(
                "Your account has been suspended. Please contact the administrator.",
                code="account_suspended",
            )

        if user.status != User.Status.ACTIVE or not user.is_active:
            raise AuthenticationFailed(
                "Your account is inactive. Please contact the administrator.",
                code="account_inactive",
            )

        self.user = user
        refresh = self.get_token(user)

        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }