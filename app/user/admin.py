
from django.contrib import admin

from .models import Token, User

admin.site.register(User)
admin.site.register(Token)


