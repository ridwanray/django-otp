from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q, F
from rest_framework import exceptions


class CustomAuthenticationBackend(ModelBackend):
    def authenticate(self, request, **kwargs):
        UserModel = get_user_model()

        try:
            username = kwargs.get(UserModel.USERNAME_FIELD, None)
            password = kwargs.get("password", None)
            if username is None or password is None:
                return None

            if user := UserModel.objects.filter(Q(email__iexact=username)).first():
                if user.is_locked:
                    raise exceptions.ValidationError(
                        {"email": "Account locked - Contact Admin"})

                if not user.is_active:
                    return None

                if user.check_password(password):
                    user.failed_login_attempts = 0
                    user.save()
                    return user
                else:
                    user.failed_login_attempts += 1

                    if user.failed_login_attempts == settings.MAX_LOGIN_ATTEMPT:
                        user.is_active = False
                        user.is_locked = True

                    user.save()
                    return None

            return None
        except UserModel.DoesNotExist:
            return None
