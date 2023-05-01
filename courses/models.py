from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation
from .fields import OrderField
from django.template.loader import render_to_string
from tinymce import models as tinymce_models
from django_quill.fields import QuillField
from django.core.validators import MaxValueValidator
import random
from django.core.exceptions import ValidationError
from django.utils.text import slugify
from unidecode import unidecode
import uuid


class Subject(models.Model):
    title = models.CharField("Тема", max_length=200)
    slug = models.SlugField(max_length=200, unique=True)

    class Meta:
        ordering = ["title"]

    def __str__(self):
        return self.title


class Course(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="courses_created",
        on_delete=models.CASCADE,
    )
    subject = models.ForeignKey(
        Subject, related_name="courses", on_delete=models.CASCADE, verbose_name="Тема"
    )
    students = models.ManyToManyField(
        settings.AUTH_USER_MODEL, related_name="courses_joined", blank=True
    )
    title = models.CharField("Название", max_length=200)
    slug = models.SlugField(
        "Слаг", max_length=200, unique=True, blank=True, help_text="Необязательно. Отображаемая адресная строка курса"
    )
    overview = models.TextField("Описание")
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            original_slug = slugify(unidecode(self.title))
            if Course.objects.filter(slug=original_slug).exists():
                self.slug = f"{original_slug}-{uuid.uuid4().hex[:6]}"
            else:
                self.slug = original_slug

        return super().save(*args, **kwargs)


class Module(models.Model):
    course = models.ForeignKey(Course, related_name="modules", on_delete=models.CASCADE)
    title = models.CharField(verbose_name="Название", max_length=200)
    description = models.TextField(verbose_name="Описание", blank=True)
    order = OrderField(blank=True, for_fields=["course"])

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.order}. {self.title}"


class Content(models.Model):
    module = models.ForeignKey(
        Module,
        related_name="contents",
        on_delete=models.CASCADE,
    )
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        limit_choices_to={
            # Content types:
            "model__in": ("text", "video", "image", "file", "htmltext", "task", "quiz")
        },
    )
    object_id = models.PositiveIntegerField()
    item = GenericForeignKey("content_type", "object_id")
    order = OrderField(blank=True, for_fields=["module"])

    class Meta:
        ordering = ["order"]


class ItemBase(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="%(class)s_related",
        on_delete=models.CASCADE,
    )
    title = models.CharField(max_length=250, verbose_name="Название")
    # Reverse generic relations f.e.
    # task.contents.all() & Content.objects.get(item_object=task) & task.contents.get(item_object=task) - ошибки
    # Content.objects.get(content_type__model="model_name", object_id=object_pk) - верный вариант
    contents = GenericRelation(Content, related_query_name="item_object")
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.title

    def render(self):
        return render_to_string(
            f"courses/content/{self._meta.model_name}.html", {"item": self}
        )


class HtmlText(ItemBase):
    """TinyMCE поле"""

    content = tinymce_models.HTMLField(verbose_name="Редактор")


class Text(ItemBase):
    content = models.TextField(verbose_name="Текст")


class File(ItemBase):
    file = models.FileField(upload_to="files/", verbose_name="Файл")


class Image(ItemBase):
    file = models.FileField(upload_to="images/", verbose_name="Изображение")


class Video(ItemBase):
    url = models.URLField()


class Task(ItemBase):
    """Задание для студентов"""

    content = QuillField(verbose_name="Инструкции")
    file = models.FileField(
        verbose_name="Файл",
        upload_to="tasks/",
        blank=True,
        help_text="Если требуется прикрепите файл",
    )
    max_score = models.PositiveIntegerField(
        verbose_name="Маскимальный балл",
        blank=True,
        default=100,
        validators=[MaxValueValidator(limit_value=100)],
        help_text="Укажите максимальный балл, который может получить студент за это задание от 0 до 100 (по умолчанию 100)",
    )
    deadline = models.DateTimeField(
        verbose_name="Срок сдачи", blank=True, null=True, help_text="Необязательно"
    )


DIFF_CHOICES = (
    ("easy", "легкий"),
    ("medium", "средний"),
    ("hard", "сложный"),
)


class Quiz(ItemBase):
    """Тест проверки знаний"""

    topic = models.CharField(verbose_name="Тема теста", max_length=120)
    number_of_questions = models.IntegerField(
        verbose_name="Количество вопросов",
        help_text="Количество отображаемых вопросов у студента (фактически их может быть больше)",
    )
    number_of_answers = models.IntegerField(
        default=5, verbose_name="Количество вариантов ответа", help_text="По умолчанию 5",
    )
    time = models.IntegerField(
        verbose_name="Время на тест в минутах",
        blank=True,
        null=True,
        help_text="Необязательно",
    )
    required_score_to_pass = models.IntegerField(
        verbose_name="Требуемый результат для прохождения теста (в процентах %)",
        help_text="На какое минимальное количество правильных процентов вопросов должен ответить студент",
    )
    deadline = models.DateTimeField(
        verbose_name="Срок сдачи",
        blank=True,
        null=True,
        help_text="Необязательно",
    )

    difficulty = models.CharField(
        verbose_name="Сложность", default="medium", max_length=6, choices=DIFF_CHOICES,
    )

    class Meta:
        verbose_name_plural = "Quizes"

    def __str__(self):
        return f"{self.topic} - {self.title}"

    def clean(self):
        super().clean()
        if self.required_score_to_pass:
            if self.required_score_to_pass > 100:
                raise ValidationError({
                    "required_score_to_pass": "Количество процентов правильных ответов не может быть больше 100%",
                })
            if self.required_score_to_pass < 0:
                raise ValidationError({
                    "required_score_to_pass": "Количество процентов правильных ответов не может быть меньше 0%",
                })

    def get_questions(self):
        """Если вопросов больше чем в self.number_of_questions,
        перемешиваем вопросы и выводим их количество равное значению self.number_of_questions"""
        questions = list(self.questions.all())
        random.shuffle(questions)
        return questions[: self.number_of_questions]


class Question(models.Model):
    """Вопрос"""

    quiz = models.ForeignKey(
        Quiz,
        related_name="questions",
        on_delete=models.CASCADE,
    )
    text = models.CharField(verbose_name="Вопрос", max_length=200)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return str(self.text)

    def get_answers(self):
        return self.answers.all()


class Answer(models.Model):
    """Ответ на вопрос"""

    text = models.CharField(verbose_name="Вариант ответа", max_length=200)
    correct = models.BooleanField(verbose_name="Правильный вариант", default=False)
    question = models.ForeignKey(
        Question,
        related_name="answers",
        on_delete=models.CASCADE,
    )
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"question: {self.question.text}, answer: {self.text}, correct: {self.correct}"
