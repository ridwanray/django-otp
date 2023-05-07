from django.contrib.auth.base_user import BaseUserManager
from django.utils.translation import gettext_lazy as _
from .enums import SystemRoleEnum


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where username is the unique identifiers
    """

    def create_user_with_phone(self, phone, **extra_fields):
        """
        Create and save a User with the given username and password.
        """
        if not phone:
            raise ValueError(_('Phone must be set'))
        user = self.model(phone=phone, is_active=True,
                          verified=True, roles = [SystemRoleEnum.CUSTOMER,], **extra_fields)
        user.save()
        return user

    def create_user(self, phone, password, **extra_fields):
        """
        Create and save a User with the given phone and password.
        """
        if not phone:
            raise ValueError(_('Phone must be set'))
        user = self.model(phone=phone, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, phone, password, **extra_fields):
        """
        Create and save a SuperUser with the given phone and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('verified', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        user = self.create_user(phone, password, **extra_fields)
        user.roles = [SystemRoleEnum.ADMIN,]
        user.save()
