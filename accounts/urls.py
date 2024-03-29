from django.urls import path, include
from django.contrib.auth import views as auth_views
from . import views
from django.views.decorators.cache import cache_page
import allauth.account.views


urlpatterns = [
    # path("login/", auth_views.LoginView.as_view(), name="login"),
    # path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    # path("register/", views.UserRegistrationView.as_view(), name="user_registration"),

    path("", include("allauth.urls")),

    path(
        "enroll-course/",
        views.StudentEnrollCourseView.as_view(),
        name="student_enroll_course",
    ),
    path("request-teacher-status/", views.request_teacher_status, name="request_teacher_status"),
    path("courses/", views.StudentCourseListView.as_view(), name="student_course_list"),
    path("courses/<course_pk>/unsubscribe/", views.unsubscribe_course, name="unsubscribe_course"),
    path(
        "course/<pk>/",
        # cache_page(60 * 15)(views.StudentCourseDetailView.as_view()),
        views.StudentCourseDetailView.as_view(),
        name="student_course_detail",
    ),
    path(
        "course/<pk>/<module_id>/",
        # cache_page(60 * 15)(views.StudentCourseDetailView.as_view()),
        views.StudentCourseDetailView.as_view(),
        name="student_course_detail_module",
    ),
    path(
        "course/task/student-answer/<pk>/",
        views.StudentAnswerDetailView.as_view(),
        name="student_answer_detail",
    ),
    path(
        "course/task/<task_id>/student-answer/new",
        views.StudentAnswerCreateView.as_view(),
        name="student_answer_new",
    ),
    path(
        "course/task/<task_pk>/student-answer/<answer_pk>/update/",
        views.StudentAnswerUpdateView.as_view(),
        name="student_answer_update",
    ),
    path(
        "course/task/<task_pk>/student-answer/<answer_pk>/delete/",
        views.StudentAnswerDeleteView.as_view(),
        name="student_answer_delete",
    ),
]
