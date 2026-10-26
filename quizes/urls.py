from django.urls import path
from .views import (
    QuizListView,
    QuizDetailView,
    QuizDataView,
    QuizSaveView,
    QuizCreateView,
    QuizUpdateView,
    QuestionAnswerCreateUpdateView,
    question_delete,
)


app_name = "quizes"

urlpatterns = [
    path("", QuizListView.as_view(), name="main-view"),  # Список тестов
    path("new/", QuizCreateView.as_view(), name="quiz_new"),  # Новый тест
    path("<pk>/update/", QuizUpdateView.as_view(), name="quiz_update"),

    path(
        "<quiz_pk>/manage/",
        QuestionAnswerCreateUpdateView.as_view(),
        name="quiz_manage",
    ),  # AddQuestion
    path(
        "<quiz_pk>/manage/question/<question_pk>",
        QuestionAnswerCreateUpdateView.as_view(),
        name="quiz_question_manage",
    ),  # UpdateQuestion
    path(
        "question/<question_pk>/delete", question_delete, name="question_delete"
    ),  # DeleteQuestion

    path("<pk>/", QuizDetailView.as_view(), name="quiz-view"),  # Тест
    path("<pk>/save", QuizSaveView.as_view(), name="save-view"),
    path("<pk>/data/", QuizDataView.as_view(), name="quiz-data-view"),
]
