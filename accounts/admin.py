from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, StudentAnswer, StudentQuizResult, TeacherRequest


class CustomUserAdmin(UserAdmin):
    fieldsets = ((None, {"fields": ("middle_name",)}),) + UserAdmin.fieldsets
    add_fieldsets = (
        (None, {"fields": ("last_name", "first_name", "middle_name")}),
    ) + UserAdmin.add_fieldsets
    list_display = ("username", "email", "first_name", "last_name", "is_staff", "date_joined")
    ordering = ("-date_joined",)


class TeacherRequestAdmin(admin.ModelAdmin):
    list_display = ("get_user_full_name", "status", "created", "updated")

    def get_user_full_name(self, obj):
        """Вернуть полное имя пользователя"""
        return obj.user.get_full_name()


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(StudentAnswer)
admin.site.register(StudentQuizResult)
admin.site.register(TeacherRequest, TeacherRequestAdmin)
