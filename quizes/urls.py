from django.urls import path
from .views import (
    QuizListView,
    quiz_view,
    quiz_data_view,
    save_quiz_view,
    QuizCreateView,
    QuestionAnswerCreateUpdateView,
    question_delete,
)


app_name = "quizes"

urlpatterns = [
    path("", QuizListView.as_view(), name="main-view"),  # Список тестов
    path("new/", QuizCreateView.as_view(), name="quiz_new"),  # Новый тест

    path("<quiz_pk>/manage/", QuestionAnswerCreateUpdateView.as_view(), name="quiz_manage"), # Добавить вопрос
    # path("<quiz_pk>/manage/<question_pk>", QuestionAnswerCreateUpdateView.as_view(), name="quiz_manage"), # Добавить вопрос
    path("question/<question_pk>/delete", question_delete, name="question_delete"),
    path("<pk>/", quiz_view, name="quiz-view"),  # Тест
    path("<pk>/save", save_quiz_view, name="save-view"),
    path("<pk>/data/", quiz_data_view, name="quiz-data-view"),
]
