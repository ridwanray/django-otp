from django.contrib.auth import get_user_model
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import filters, serializers, status, viewsets
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_simplejwt.views import TokenObtainPairView

from .enums import TokenEnum
from .filters import UserFilter
from .models import Token, User
from .serializers import (AuthTokenSerializer,OnboardUserSerializer,
                          CreatePasswordFromResetOTPSerializer,
                          CustomObtainTokenPairSerializer, EmailSerializer,
                          ListUserSerializer, PasswordChangeSerializer,
                          AccountVerificationSerializer,InitiatePasswordResetSerializer,
                          UpdateUserSerializer)
from .utils import IsAdmin,  is_admin_user


class CustomObtainTokenPairView(TokenObtainPairView):
    """Authentice with phone number and password"""
    serializer_class = CustomObtainTokenPairSerializer


class AuthViewsets(viewsets.GenericViewSet):
    """Auth viewsets"""
    serializer_class = EmailSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["initiate_password_reset", "create_password", "verify_account"]:
            permission_classes = [AllowAny]
        return [permission() for permission in permission_classes]

    @action(
        methods=["POST"],
        detail=False,
        serializer_class=InitiatePasswordResetSerializer,
        url_path="initiate-password-reset",
    )
    def initiate_password_reset(self, request, pk=None):
        """Send temporary OTP to user phone to be used for password reset"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True,
                         "message": "Temporary password sent to your mobile!"}, status=200)

    @action(methods=['POST'], detail=False, serializer_class=CreatePasswordFromResetOTPSerializer, url_path='create-password')
    def create_password(self, request, pk=None):
        """Create a new password given the reset OTP sent to user phone number"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token: Token = Token.objects.filter(
            token=request.data['otp'],  token_type=TokenEnum.PASSWORD_RESET).first()
        if not token or not token.is_valid():
            return Response({'success': False, 'errors': 'Invalid password reset otp'}, status=400)
        token.reset_user_password(request.data['new_password'])
        token.delete()
        return Response({'success': True, 'message': 'Password successfully reset'}, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: inline_serializer(
                name='AccountVerificationStatus',
                fields={
                    "success": serializers.BooleanField(default=True),
                    "message": serializers.CharField(default="Acount Verification Successful")
                }
            ),
        },
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=AccountVerificationSerializer,
        url_path="verify-account",
    )
    def verify_account(self, request, pk=None):
        """Activate a user acount using the verification(OTP) sent to the user phone"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "Acount Verification Successful"}, status=200)


class PasswordChangeView(viewsets.GenericViewSet):
    '''Allows password change to authenticated user.'''
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        context = {"request": request}
        serializer = self.get_serializer(data=request.data, context=context)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"message": "Your password has been updated."}, status.HTTP_200_OK)


class CreateTokenView(ObtainAuthToken):
    """Create a new auth token for user"""

    serializer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request, *args, **kwargs):
        serializer = self.serializer_class(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        try:
            token, created = Token.objects.get_or_create(user=user)
            return Response(
                {"token": token.key, "created": created, "roles": user.roles},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response({"message": str(e)}, 500)


class UserViewsets(viewsets.ModelViewSet):
    queryset = get_user_model().objects.all()
    serializer_class = ListUserSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete"]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = UserFilter
    search_fields = ["email", "firstname", "lastname", "phone"]
    ordering_fields = [
        "created_at",
        "email",
        "firstname",
        "lastname",
        "phone",
    ]

    def get_queryset(self):
        user: User = self.request.user
        if is_admin_user(user):
            return super().get_queryset().all()
        return super().get_queryset().filter(id=user.id)

    def get_serializer_class(self):
        if self.action == "create":
            return OnboardUserSerializer
        if self.action in ["partial_update", "update"]:
            return UpdateUserSerializer
        return super().get_serializer_class()

    def get_permissions(self):
        permission_classes = self.permission_classes
        if self.action in ["create"]:
            permission_classes = [AllowAny]
        elif self.action in ["list", "retrieve", "partial_update", "update"]:
            permission_classes = [IsAuthenticated]
        elif self.action in ["destroy"]:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]
    

    @extend_schema(
        responses={
            200: inline_serializer(
                name='VerificationStatus',
                fields={
                    "success": serializers.BooleanField(default=True),
                    "message": serializers.CharField(default="OTP sent for verification!")
                }
            ),
        },
        description="Sign up with a validate phone number. i.e. 08130303030 or +2348130303030"
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"success": True, "message": "OTP sent for verification!"}, status=200)

    def list(self, request, *args, **kwargs):
        "Retrieve user lists based on assigned role"
        return super().list(request, *args, **kwargs)
