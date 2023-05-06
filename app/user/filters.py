import django_filters

from .enums import ROLE_CHOICE
from .models import User


class UserFilter(django_filters.FilterSet):   
    class Meta:
        model = User
        fields = ['verified']