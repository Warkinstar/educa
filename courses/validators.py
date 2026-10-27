import os
from django.core.exceptions import ValidationError
from PIL import Image as PilImage


ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}
MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024  # 10 МБ


def validate_image_file_extension(value):
    """
    Проверяет расширение файла. SVG категорически запрещен из-за риска XSS.
    """
    name = getattr(value, "name", "")
    ext = os.path.splitext(name)[1].lower().lstrip(".")
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        allowed = ", ".join(f".{e}" for e in sorted(ALLOWED_IMAGE_EXTENSIONS))
        raise ValidationError(
            f"Недопустимый формат файла «.{ext}». Разрешены только изображения: {allowed} (формат SVG запрещен)."
        )


def validate_image_file_size(value):
    """
    Проверяет размер файла: не более 10 МБ.
    """
    size = getattr(value, "size", 0)
    if size > MAX_IMAGE_SIZE_BYTES:
        max_mb = MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
        size_mb = round(size / (1024 * 1024), 2)
        raise ValidationError(
            f"Размер файла ({size_mb} МБ) превышает максимально допустимый ({max_mb} МБ)."
        )


def validate_real_image(value):
    """
    Комплексная валидация:
    1. Расширение имени файла.
    2. Размер файла (<= 10 МБ).
    3. Проверка через Pillow, что байты файла соответствуют валидному изображению.
    """
    validate_image_file_extension(value)
    validate_image_file_size(value)

    if hasattr(value, "seek") and callable(value.seek):
        value.seek(0)

    try:
        image = PilImage.open(value)
        image.verify()

        format_name = (image.format or "").lower()
        valid_pillow_formats = {"jpeg", "png", "gif", "webp"}
        if format_name not in valid_pillow_formats:
            raise ValidationError("Неподдерживаемый тип содержимого изображения.")
    except Exception as exc:
        if isinstance(exc, ValidationError):
            raise
        raise ValidationError("Загруженный файл поврежден или не является допустимым изображением.")
    finally:
        if hasattr(value, "seek") and callable(value.seek):
            value.seek(0)