from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    fieldsets = (
        (None, {"fields": ("middle_name",)}),
    ) + UserAdmin.fieldsets 
    add_fieldsets = (
        (None, {"fields": ("last_name", "first_name", "middle_name")}),
    ) + UserAdmin.add_fieldsets 

admin.site.register(CustomUser, CustomUserAdmin)
