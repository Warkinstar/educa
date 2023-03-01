from django.urls import path
from .views import (
    QuizListView,
    quiz_view,
    quiz_data_view,
    save_quiz_view,
    QuizCreateView,
    QuestionAnswerCreateView,
)


app_name = "quizes"

urlpatterns = [
    path("", QuizListView.as_view(), name="main-view"),  # Список тестов
    path("new/", QuizCreateView.as_view(), name="quiz_new"),  # Новый тест
    path("<quiz_pk>/question/add/", QuestionAnswerCreateView.as_view(), name="question_add"), # Добавить вопрос
    path("<pk>/", quiz_view, name="quiz-view"),  # Тест
    path("<pk>/save", save_quiz_view, name="save-view"),
    path("<pk>/data/", quiz_data_view, name="quiz-data-view"),
]
