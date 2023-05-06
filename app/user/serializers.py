from datetime import datetime, timezone

from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import exceptions, serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .enums import TokenEnum
from .models import PendingUser, Token, User
from .tasks import send_phone_notification
from .utils import clean_phone, generate_otp, is_admin_user


class CustomObtainTokenPairSerializer(TokenObtainPairSerializer):

    def validate(self, attrs):
        data = super().validate(attrs)
        refresh = self.get_token(self.user)
        access_token = refresh.access_token
        self.user.save_last_login()
        data['refresh'] = str(refresh)
        data['access'] = str(access_token)
        return data

    @classmethod
    def get_token(cls, user: User):
        if not user.verified:
            raise exceptions.AuthenticationFailed(
                _('Account not verified.'), code='authentication')
        token = super().get_token(user)
        token.id = user.id
        token['firstname'] = user.firstname
        token['lastname'] = user.lastname
        token["email"] = user.email
        token["roles"] = user.roles
        return token


class AuthTokenSerializer(serializers.Serializer):
    """Serializer for user authentication object"""

    email = serializers.CharField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False)

    def validate(self, attrs):
        """Validate and authenticate the user"""
        email = attrs.get("email")
        password = attrs.get("password")
        if email:
            user = authenticate(request=self.context.get(
                "request"), username=email.lower().strip(), password=password)

        if not user:
            msg = _("Unable to authenticate with provided credentials")
            raise serializers.ValidationError(msg, code="authentication")
        attrs["user"] = user
        return attrs


class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(max_length=128, required=False)
    new_password = serializers.CharField(max_length=128, min_length=5)

    def validate_old_password(self, value):
        request = self.context["request"]

        if not request.user.check_password(value):
            raise serializers.ValidationError("Old password is incorrect.")
        return value

    def save(self):
        user: User = self.context["request"].user
        new_password = self.validated_data["new_password"]
        user.set_password(new_password)
        user.save(update_fields=["password"])


class CreatePasswordFromTokenSerializer(serializers.Serializer):
    otp = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)


class AccountVerificationSerializer(serializers.Serializer):
    otp = serializers.IntegerField(required=True)
    phone = serializers.CharField(required=True, allow_blank=False)

    def validate(self, attrs: dict):
        phone_number: str = attrs.get('phone').strip().lower()
        mobile: str = clean_phone(phone_number)
        pending_user: PendingUser = PendingUser.objects.filter(
            phone=mobile, verification_code=attrs.get('otp')).first()
        if pending_user and pending_user.is_valid():
            attrs['phone'] = mobile
            attrs['password'] = pending_user.password
            attrs['pending_user'] = pending_user
        else:
            raise serializers.ValidationError(
                {'otp': 'Verification failed. Invalid OTP or Number'})
        return super().validate(attrs)

    @transaction.atomic
    def create(self, validated_data: dict):
        validated_data.pop('otp')
        pending_user = validated_data.pop('pending_user')
        User.objects.create_user_with_phone(**validated_data)
        pending_user.delete()
        return validated_data


class EmailSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PhoneSerializer(serializers.Serializer):
    phone = serializers.CharField(required=True, allow_blank=False)

    def validate(self, attrs: dict):
        phone = attrs.get('phone')
        strip_number = phone.lower().strip()
        mobile = clean_phone(strip_number)
        user = get_user_model().objects.filter(phone=mobile, is_active=True).first()
        if not user:
            raise serializers.ValidationError({'phone':'Phone number not registered.'})
        attrs['phone'] = mobile
        attrs['user'] =  user
        return super().validate(attrs)
    
    def create(self, validated_data):
        phone = validated_data.get('phone')
        user = validated_data.get('user')
        otp = generate_otp()
        token,_ = Token.objects.update_or_create(
            user=user,
            token_type=TokenEnum.PASSWORD_RESET,
            defaults={
                "user": user,
                "token_type": TokenEnum.PASSWORD_RESET,
                "token": otp,
                "created_at": datetime.now(timezone.utc)
            }
        )

        message_info = {
            'message': f"Password Reset!\nUse {otp} to reset your password.\nIt expires in 10 minutes",
            'phone': phone
        }

        send_phone_notification.delay(message_info)
        return token


class ListUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "firstname",
            "lastname",
            "email",
            "image",
            "verified",
            "created_at",
            "roles",
        ]

        extra_kwargs = {
            "verified": {"read_only": True},
            "roles": {"read_only": True},
        }

    def to_representation(self, instance):
        return super().to_representation(instance)


class UpdateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "firstname",
            "lastname",
            "image",
            "verified",
            "roles"
        ]
        extra_kwargs = {
            "last_login": {"read_only": True},
            "verified": {"read_only": True},
            "roles": {"required": False},
        }

    def validate(self, attrs: dict):
        """Only allow admin to modify/assign role"""
        auth_user: User = self.context["request"].user
        new_role_assignment = attrs.get("roles", None)
        if new_role_assignment and is_admin_user(auth_user):
            pass
        else:
            attrs.pop('roles', None)
        return super().validate(attrs)

    def update(self, instance, validated_data):
        """Prevent user from updating password"""
        if validated_data.get("password", False):
            validated_data.pop('password')
        instance = super().update(instance, validated_data)
        return instance


class BasicUserInfoSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "firstname",
            "lastname",
        ]


class OnboardUserSerializer(serializers.Serializer):
    """Serializer for creating user object"""
    phone = serializers.CharField(required=True, allow_blank=False)
    password = serializers.CharField(min_length=6)

    def validate(self, attrs: dict):
        phone = attrs.get('phone')
        strip_number = phone.lower().strip()
        cleaned_number = clean_phone(strip_number)
        if get_user_model().objects.filter(phone__iexact=cleaned_number).exists():
            raise serializers.ValidationError(
                {'phone': 'Phone number already exists'})
        attrs['phone'] = cleaned_number
        return super().validate(attrs)

    def create(self, validated_data: dict):
        otp = generate_otp()
        phone_number = validated_data.get('phone')
        user, _ = PendingUser.objects.update_or_create(
            phone=phone_number,
            defaults={
                "phone": phone_number,
                "verification_code": otp,
                "password": make_password(validated_data.get('password')),
                "created_at": datetime.now(timezone.utc)
            }
        )
        message_info = {
            'message': f"Account Verification!\nYour OTP for BotoApp is {otp}.\nIt expires in 10 minutes",
            'phone': user.phone
        }
        send_phone_notification.delay(message_info)
        return user
