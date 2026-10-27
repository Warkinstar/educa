import uuid
from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models

from .validators import validate_comment_file


class AbstractModel(models.Model):
    id = models.BigAutoField(primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        abstract = True


class Comment(AbstractModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Автор"
    )
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Родительский комментарий"
    )

    # Полиморфная связь (к Module или любой другой модели)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveBigIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    text = models.TextField(verbose_name="Текст комментария")
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Комментарий от {self.user} к {self.content_object} (#{self.pk})"


def comment_file_upload_to(instance, filename):
    return f"comments/files/{instance.comment.id}/{uuid.uuid4().hex[:8]}_{filename}"


class CommentFile(AbstractModel):
    comment = models.ForeignKey(
        Comment,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Комментарий"
    )
    file = models.FileField(
        upload_to=comment_file_upload_to,
        validators=[validate_comment_file],
        verbose_name="Файл"
    )
    filename = models.CharField(max_length=255, blank=True, verbose_name="Исходное имя файла")

    class Meta:
        verbose_name = "Файл комментария"
        verbose_name_plural = "Файлы комментариев"

    def save(self, *args, **kwargs):
        if self.file and not self.filename:
            self.filename = self.file.name.split('/')[-1]
        super().save(*args, **kwargs)

    def __str__(self):
        return self.filename or f"File #{self.pk}"