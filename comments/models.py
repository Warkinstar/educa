import os
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone

from comments.validators import validate_file_extension, validate_file_size


class AbstractModel(models.Model):
    """Базовая абстрактная модель с public_id и временными метками."""
    public_id = models.UUIDField(db_index=True, unique=True, default=uuid.uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class AbstractCommentFile(AbstractModel):
    """Абстрактная модель, обобщающая поля для CommentFile."""
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Кем загружен",
    )
    filename = models.CharField("Имя файла", editable=False, max_length=1000, null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self):
        return self.filename or (self.file.name if self.file else "Файл не указан")

    @property
    def _filename(self):
        return os.path.basename(self.file.name)

    @property
    def file_extension(self):
        if self.file and self.file.name:
            return self.file.name.split(".")[-1].lower()
        return ""


class Comment(AbstractModel):
    """Универсальный комментарий к любому объекту."""

    # Универсальная связь
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    target_public_id = models.UUIDField(
        db_index=True,
        default=None,
        null=True,
        blank=True,
        editable=False,
        verbose_name="public_id целевого экземпляра модели",
    )
    content_object = GenericForeignKey("content_type", "object_id")

    # Структура комментариев
    mention = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentions_in_comments",
        verbose_name="Упомянутый пользователь",
        help_text="Пользователь, которого отметили в комментарии",
    )
    reply_to = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Родительский комментарий",
        help_text="Для вложенных комментариев (ответов)",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="comments",
        verbose_name="Автор",
    )
    text = models.TextField(verbose_name="Текст комментария")
    metadata = models.JSONField(
        encoder=DjangoJSONEncoder,
        default=dict,
        blank=True,
        verbose_name="Данные записи",
    )

    class Meta:
        indexes = [
            models.Index(fields=["content_type", "object_id"]),
        ]
        verbose_name = "Комментарий (универсальный)"
        verbose_name_plural = "Комментарии (универсальные)"
        ordering = ["created"]

    def __str__(self):
        obj = self.content_object
        return f"Комментарий от {self.created_by} к {obj}" if obj else f"Комментарий от {self.created_by}"

    @property
    def can_be_deleted_by_author(self):
        return timezone.now() - self.created <= timedelta(hours=3)

    def clean(self):
        super().clean()
        if self.reply_to and self.pk:
            if (
                self.reply_to.content_type_id != self.content_type_id
                or self.reply_to.object_id != self.object_id
            ):
                raise ValidationError("Родительский комментарий должен относиться к тому же объекту.")

    def save(self, *args, **kwargs):
        self.clean()
        if self.content_object:
            self.target_public_id = getattr(self.content_object, "public_id", None)
        super().save(*args, **kwargs)


class CommentFile(AbstractCommentFile):
    """Файл, прикреплённый к универсальному комментарию."""
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="files",
        null=True,
        blank=True,
        verbose_name="Комментарий",
    )
    upload_session_id = models.UUIDField(
        default=None,
        null=True,
        blank=True,
        db_index=True,
        editable=False,
        verbose_name="ID сессии загрузки",
    )
    file = models.FileField(
        upload_to="comments/files/%Y/%m/",
        validators=[validate_file_extension, validate_file_size],
        verbose_name="Файл",
    )

    class Meta:
        verbose_name = "Файл комментария (общий)"
        verbose_name_plural = "Файлы комментариев (общие)"
        ordering = ["-created"]

    @classmethod
    def bind_files_to_comment(cls, upload_session_id, comment):
        cls.objects.filter(
            upload_session_id=upload_session_id,
            comment__isnull=True,
        ).update(
            comment=comment,
            upload_session_id=None,
        )

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self._filename
        super().save(*args, **kwargs)