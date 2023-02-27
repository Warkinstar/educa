from django.db import models
from django.contrib.auth.models import AbstractUser
from courses.models import Task, Quiz
from django.conf import settings
from django.core.validators import MaxValueValidator
from django_quill.fields import QuillField
from django.urls import reverse
from django.core.exceptions import ValidationError


class CustomUser(AbstractUser):
    middle_name = models.CharField(("Отчество"), max_length=150, blank=True)


class StudentAnswer(models.Model):
    """Ответ студента на задание"""

    # Отношения
    task = models.ForeignKey(Task, related_name="answers", on_delete=models.CASCADE)
    student = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="task_answers",
        on_delete=models.CASCADE,
    )
    # Поля для студента
    title = models.CharField(max_length=250, verbose_name="Подпись")
    content = QuillField(verbose_name="Ответ")
    file = models.FileField(
        upload_to="answer_files",
        blank=True,
        help_text="Если требуется, прикрепите файл",
    )

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # Поля для учителя
    comment = QuillField(
        verbose_name="Комментарий", blank=True, help_text="Комментарий преподователя"
    )
    check_date = models.DateField(verbose_name="Дата проверки", blank=True, null=True)
    score = models.PositiveIntegerField(
        verbose_name="Оценка за ответ студента",
        validators=[
            MaxValueValidator(limit_value=100),
        ],
        blank=True,
        null=True,
    )

    class Meta:
        ordering = ["score"]

    def __str__(self):
        return f"Ответ от: {self.student.get_full_name()}"

    def clean(self):
        super().clean()
        if self.score is not None and self.task_id is not None:
            if self.score > self.task.max_score:
                raise ValidationError(
                    {
                        "score": "Оценка не может быть больше, чем максимальный балл задания"
                    }
                )

    def get_absolute_url(self):
        return reverse("student_answer_detail", kwargs={"pk": self.pk})


class StudentQuizResult(models.Model):
    """Результат студента за тест"""

    quiz = models.ForeignKey(
        Quiz,
        related_name="results",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="quiz_results",
        on_delete=models.CASCADE,
    )
    score = models.FloatField(verbose_name="Процент правильных ответов")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} | Тест: {self.quiz} | Результат: {self.score}%"
