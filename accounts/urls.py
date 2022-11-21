from django.urls import path
from django.contrib.auth import views as auth_views
from . import views


urlpatterns = [
    path("login/", auth_views.LoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("register/", views.UserRegistrationView.as_view(), name="user_registration"),
    path(
        "enroll-course/",
        views.StudentEnrollCourseView.as_view(),
        name="student_enroll_course",
    ),
    path("courses/", views.StudentCourseListView.as_view(), name="student_course_list"),
    path(
        "course/<pk>/",
        views.StudentCourseDetailView.as_view(),
        name="student_course_detail",
    ),
    path(
        "course/<pk>/<module_id>/",
        views.StudentCourseDetailView.as_view(),
        name="student_course_detail_module",
    ),
]
