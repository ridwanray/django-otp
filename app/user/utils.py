import base64
import os
import re
from datetime import datetime, timezone
from typing import Any, Dict

import pyotp
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.crypto import get_random_string
from rest_framework import permissions, serializers
from twilio.rest import Client

from .enums import SystemRoleEnum
from .models import Token, User

client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

def get_user_role_names(user:User)->list:
    """
    Returns a list of role names for the given user.
    """
    return user.roles.values_list('name', flat=True)

def is_admin_user(user:User)->bool:
    """
    Check an authenticated user is an admin or not
    """
    return user.is_admin or SystemRoleEnum.ADMIN in user.roles


class IsAdmin(permissions.BasePermission):
    """Allows access only to Admin users."""
    message = "Only Admins are authorized to perform this action."
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return  is_admin_user(request.user)
    

def send_sms(message:str, phone:str):
    client.messages.create(
                              body=message,
                              from_=settings.TWILIO_PHONE_NUMBER,
                              to=phone
                          )
    return


def clean_phone(number:str):
        """Validates number start with +234 or 0, then 10 digits"""
        number_pattern = re.compile(r'^(?:\+234|0)\d{10}$')
        result = number_pattern.match(number)
        if result:
            if number.startswith('0'): 
                return '+234' + number[1:]
            return number
        else:
            raise serializers.ValidationError({'phone': 'Incorrect phone number.'})    
        

def generate_otp()->int:
    totp = pyotp.TOTP(base64.b32encode(os.urandom(16)).decode('utf-8'))
    otp = totp.now()
    return otp