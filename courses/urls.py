from django.urls import path
from . import views
from django.views.decorators.cache import cache_page

urlpatterns = [
    # Главная страница управления курсами (с поиском, фильтрами и пагинацией)
    path("mine/", views.ManageCourseListView.as_view(), name="manage_course_list"),

    # Модальные окна управления курсами
    path("modal/create/", views.CourseCreateModalView.as_view(), name="course_modal_create"),
    path("modal/<int:pk>/edit/", views.CourseUpdateModalView.as_view(), name="course_modal_update"),
    path("modal/<int:pk>/delete/", views.CourseDeleteModalView.as_view(), name="course_modal_delete"),
    path("modal/<int:pk>/modules/", views.CourseModulesManageModalView.as_view(), name="course_modal_modules"),
        path("modal/<int:pk>/students/", views.CourseStudentsModalView.as_view(), name="course_modal_students"),
    path("modal/<int:pk>/groups/", views.CourseGroupsModalView.as_view(), name="course_modal_groups"),
    path("modal/<int:pk>/progress/", views.CourseProgressModalView.as_view(), name="course_modal_progress"),
    path("modal/group-assignment/<int:pk>/deactivate/", views.CourseGroupAssignmentDeactivateView.as_view(), name="group_assignment_deactivate"),
    path("modal/group-assignment/<int:pk>/update-dates/",
        views.CourseGroupAssignmentUpdateDatesView.as_view(),
        name="group_assignment_update_dates",),
    path("modal/user-assignment/<int:pk>/deactivate/",
        views.CourseUserAssignmentDeactivateView.as_view(),
        name="user_assignment_deactivate",),
    path("modal/<int:course_pk>/students/exclude/<int:student_pk>/", views.exclude_student_from_course, name="exclude_student"),
    path("modal/subject/create/", views.SubjectCreateOffcanvasView.as_view(), name="subject_modal_create"),
    path("modal/module/add-row/", views.CourseModuleAddRowView.as_view(), name="course_module_add_row"),

    # Управление содержимым модулей и тестами
    path("module/<int:module_id>/content/<model_name>/create/", views.ContentCreateUpdateView.as_view(), name="module_content_create"),
    path("module/<int:module_id>/content/<model_name>/<id>/", views.ContentCreateUpdateView.as_view(), name="module_content_update"),
    path("module/content/quiz/<quiz_pk>/manage/", views.CourseQuizQuestionAnswerCreateUpdateView.as_view(), name="course_quiz_manage"),
    path("module/content/quiz/<quiz_pk>/question/<question_pk>/manage", views.CourseQuizQuestionAnswerCreateUpdateView.as_view(), name="course_quiz_question_manage"),
    path("module/<int:module_id>/", views.ModuleContentListView.as_view(), name="module_content_list"),
    path("module/<module_pk>/content/<content_pk>/delete", views.content_delete, name="module_content_delete"),
    path("module/<int:module_pk>/task/<int:task_pk>/answers/", views.TaskDetailView.as_view(), name="module_task_detail"),
    path("module/<int:module_pk>/quiz/<int:quiz_pk>/results/", cache_page(60 * 15)(views.StudentQuizResultsListView.as_view()), name="module_quiz_results"),
    path("module/task/<int:task_pk>/answer/<int:answer_pk>/check/", views.StudentAnswerCheckUpdateView.as_view(), name="answer_check_update"),
    path("module/order/", views.ModuleOrderView.as_view(), name="module_order"),
    path("content/order/", views.ContentOrderView.as_view(), name="content_order"),
    path("subject/<slug:subject>/", views.CourseListView.as_view(), name="course_list_subject"),
    path("teacher-courses/<int:teacher_pk>/", views.CourseListView.as_view(), name="course_list_teacher"),
    path("<slug:slug>/", views.CourseDetailView.as_view(), name="course_detail"),
    path("module/<int:module_id>/content/<model_name>/<id>/upload_image", views.upload_image, name="upload_image"),
    path("manage/groups/", views.StudyGroupListView.as_view(), name="study_group_list"),
    path("manage/groups/create/", views.StudyGroupCreateView.as_view(), name="study_group_create"),
    path("manage/groups/<int:pk>/edit/", views.StudyGroupUpdateView.as_view(), name="study_group_update"),
    path("manage/groups/<int:pk>/delete/", views.StudyGroupDeleteView.as_view(), name="study_group_delete"),
    path('<int:pk>/analytics/', views.CourseAnalyticsView.as_view(), name='course_analytics',),
    path('<int:pk>/analytics/export/', views.CourseAnalyticsExportView.as_view(), name='course_analytics_export',),
]
