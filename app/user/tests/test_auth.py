from datetime import datetime, timedelta

import pytest
import time_machine
from decouple import config
from django.urls import reverse
from rest_framework import status
from user.enums import TokenEnum
from user.models import Token

from .conftest import api_client_with_credentials


pytestmark = pytest.mark.django_db


class TestAuthEndpoints:
    initiate_password_reset_url = reverse(
        'auth:auth-initiate-password-reset')
    password_change_url = reverse('auth:password-change-list')

    login_url = reverse("auth:login")
    verify_account_url = reverse("auth:auth-verify-account")
    create_password_via_reset_token_url = reverse("auth:auth-create-password")

    def test_user_login(self, api_client, active_user, auth_user_password):
        data = {
            "email": active_user.email,
            "password": auth_user_password}
        response = api_client.post(self.login_url, data)
        assert response.status_code == status.HTTP_200_OK
        returned_json = response.json()
        assert 'refresh' in returned_json
        assert 'access' in returned_json

    def test_deny_login_to_inactive_user(self, api_client, inactive_user, auth_user_password):
        data = {
            "email": inactive_user.email,
            "password": auth_user_password}
        response = api_client.post(self.login_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_deny_login_invalid_credentials(self, api_client, active_user):
        data = {
            "email": active_user.email,
            "password": "wrong@pass"}
        response = api_client.post(self.login_url, data)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_password_reset_initiate(self, mocker, api_client, active_user):
        """Initiate a password reset for not authenticated user"""
        mock_send_temporary_password_email = mocker.patch(
            'user.tasks.send_password_reset_email.delay')
        data = {
            'email': active_user.email,
            'token': '123456'
        }
        response = api_client.post(
            self.initiate_password_reset_url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        mock_send_temporary_password_email.side_effect = print(
            "Sent to celery task:Password Reset Mail!")

        token: Token = Token.objects.get(
            user=active_user,  token_type=TokenEnum.PASSWORD_RESET)
        email_token = token.token
        email_data = {
            'fullname': active_user.firstname,
            'email': active_user.email,
            'token': email_token
        }
        mock_send_temporary_password_email.assert_called_once_with(email_data)

    def test_deny_initiate_password_reset_to_inactive_user(self, api_client, inactive_user):
        data = {
            'email': inactive_user.email,
        }
        response = api_client.post(
            self.initiate_password_reset_url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_change_password_using_valid_old_password(self, api_client, authenticate_user, auth_user_password):
        user = authenticate_user()
        token = user['token']
        user_instance = user['user_instance']
        data = {
            'old_password': auth_user_password,
            'new_password': 'newpass@@',
        }
        api_client_with_credentials(token, api_client)
        response = api_client.post(
            self.password_change_url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        user_instance.refresh_from_db()
        assert user_instance.check_password('newpass@@')

    def test_deny_change_password_using_invalid_old_password(self, api_client, authenticate_user):
        user = authenticate_user()
        token = user['token']
        data = {
            'old_password': 'invalidpass',
            'new_password': 'New87ge&nerated',
        }
        api_client_with_credentials(token, api_client)
        response = api_client.post(
            self.password_change_url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_deny_change_password_for_unathenticated_user(self, api_client):
        """Only Authenticated User can change password using old valid password"""
        data = {
            'old_password': 'invalidpass',
            'new_password': 'New87ge&nerated',
        }
        response = api_client.post(
            self.password_change_url, data, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_verify_account_using_verification_token(self, api_client, user_factory, token_factory):
        unverified_user = user_factory(verified=False, is_active=False)
        verification_token: Token = token_factory(
            user=unverified_user, token_type=TokenEnum.ACCOUNT_VERIFICATION)
        request_payload = {'token': verification_token.token}
        response = api_client.post(self.verify_account_url, request_payload)
        assert response.status_code == 200
        unverified_user.refresh_from_db()
        assert unverified_user.verified == True
        assert unverified_user.is_active == True

    def test_deny_verify_using_invalid_token(self, api_client, user_factory):
        unverified_user = user_factory(verified=False, is_active=False)
        token = "sampletoken"
        request_payload = {'token': token}
        response = api_client.post(self.verify_account_url, request_payload)
        assert response.status_code == 400
        unverified_user.refresh_from_db()
        assert unverified_user.verified == False
        assert unverified_user.is_active == False

    def test_create_new_password_using_valid_reset_token(self, api_client, active_user, token_factory):
        token: Token = token_factory(
            user=active_user, token_type=TokenEnum.PASSWORD_RESET)
        data = {
            "token": token.token,
            "new_password": "new_pass_me"
        }
        response = api_client.post(
            self.create_password_via_reset_token_url, data)
        assert response.status_code == 200
        active_user.refresh_from_db()
        assert active_user.check_password('new_pass_me')

    def test_deny_create_new_password_using_invalid_reset_token(self, api_client, active_user, token_factory):
        token: Token = token_factory(
            token_type=TokenEnum.ACCOUNT_VERIFICATION, user=active_user)
        data = {
            "token": token.token,
            "new_password": "new_pass_me"
        }
        response = api_client.post(
            self.create_password_via_reset_token_url, data)
        assert response.status_code == 400

    def test_user_reinvite(self, api_client, mocker, user_factory):
        unverified_user = user_factory(verified=False)
        mock_send_user_creation_email = mocker.patch(
            'user.tasks.send_user_creation_email.delay')
        data = {
            "email": unverified_user.email
        }
        url = reverse('user:user-reinvite-user')
        response = api_client.post(url, data)
        assert response.status_code == 200
        verification_token = Token.objects.get(
            user__email=data["email"],  token_type=TokenEnum.ACCOUNT_VERIFICATION)

        email_data = {
            'fullname': unverified_user.firstname,
            'email': data.get('email'),
            'token': verification_token.token,
        }
        mock_send_user_creation_email.assert_called_once_with(email_data)

    def test_deny_user_reinvite(self, api_client, user_factory):
        unverified_user = user_factory(verified=True)
        data = {
            "email": unverified_user.email
        }
        url = reverse('user:user-reinvite-user')
        response = api_client.post(url, data)
        assert response.status_code == 400
    
    def test_account_locked_after_max_login_attempt(self, api_client, active_user):
        url = reverse('auth:login')
        assert active_user.is_active 
        data = {
            'email':active_user.email,
            'password':'wrongpass'
        }

        for _ in range(0,config('MAX_LOGIN_ATTEMPT', cast=int)) : api_client.post(url, data, format='json')
        active_user.refresh_from_db()
        assert active_user.is_active ==  False
        assert active_user.is_locked ==  True
       
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    

    def test_account_not_locked(self, api_client, active_user):
        """Account not locked when the maximum login attempts are not exceededs"""
        url = reverse('auth:login')
        assert active_user.is_active 
        data = {
            'email':active_user.email,
            'password':'wrongpass'
        }

        for _ in range(0,config('MAX_LOGIN_ATTEMPT', cast=int)-1) : api_client.post(url, data, format='json')
        active_user.refresh_from_db()
        assert active_user.is_active ==  True
        assert active_user.is_locked ==  False
        response = api_client.post(url, data, format='json')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

