from django.urls import path
from . import views
from django.views.decorators.cache import cache_page

urlpatterns = [
    path("mine/", views.ManageCourseListView.as_view(), name="manage_course_list"),
    path("create/", views.CourseCreateView.as_view(), name="course_create"),
    path("<pk>/students", views.CourseStudentsDetailView.as_view(), name="about_course_detail"),
    path("<course_pk>/students/exclude/<student_pk>", views.exclude_student_from_course, name="exclude_student"),
    path("<pk>/edit/", views.CourseUpdateView.as_view(), name="course_edit"),
    path("<pk>/delete/", views.CourseDeleteView.as_view(), name="course_delete"),
    path(
        "<pk>/module/",
        views.CourseModuleUpdateView.as_view(),
        name="course_module_update",
    ),
    path(
        "module/<int:module_id>/content/<model_name>/create/",
        views.ContentCreateUpdateView.as_view(),
        name="module_content_create",
    ),
    path(
        "module/<int:module_id>/content/<model_name>/<id>/",
        views.ContentCreateUpdateView.as_view(),
        name="module_content_update",
    ),
    # Страница добавления вопросов
    path("module/content/quiz/<quiz_pk>/manage/",
        views.CourseQuizQuestionAnswerCreateUpdateView.as_view(),
        name="course_quiz_manage"
    ),
    # Страница обновления вопроса
    path("module/content/quiz/<quiz_pk>/question/<question_pk>/manage",
         views.CourseQuizQuestionAnswerCreateUpdateView.as_view(),
         name="course_quiz_question_manage",
    ),
    # Страница контентов модуля
    path(
        "module/<int:module_id>/",
        views.ModuleContentListView.as_view(),
        name="module_content_list",
    ),
    # Удаление контента
    path(
        "module/<module_pk>/content/<content_pk>/delete",
        views.content_delete,
        name="module_content_delete",
    ),
    # Страница списка ответов на задание
    path(
        "module/<int:module_pk>/task/<int:task_pk>/answers/",
        views.TaskDetailView.as_view(),
        name="module_task_detail",
    ),
    # Страница результатов на тест
    path(
        "module/<int:module_pk>/quiz/<int:quiz_pk>/results/",
        cache_page(60 * 15)(views.StudentQuizResultsListView.as_view()),
        name="module_quiz_results",
    ),
    path(
        "module/task/<int:task_pk>/answer/<int:answer_pk>/check/",
        views.StudentAnswerCheckUpdateView.as_view(),
        name="answer_check_update",
    ),
    path("module/order/", views.ModuleOrderView.as_view(), name="module_order"),
    path("content/order/", views.ContentOrderView.as_view(), name="content_order"),
    path(
        "subject/<slug:subject>/",
        views.CourseListView.as_view(),
        name="course_list_subject",
    ),
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="course_detail"),
    path(
        "module/<int:module_id>/content/<model_name>/<id>/upload_image",  # Изображения для tinymce
        views.upload_image,
        name="upload_image",
    ),
]
