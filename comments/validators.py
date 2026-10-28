import os
from django.core.exceptions import ValidationError

ALLOWED_FILE_EXTENSIONS = {
    ".ppt",
    ".pptx",
    ".odp",
    ".xlsx",
    ".xls",
    ".ods",
    ".docx",
    ".doc",
    ".odt",
    ".txt",
    ".rtf",
    ".bmp",
    ".jpeg",
    ".wbmp",
    ".gif",
    ".png",
    ".jpg",
    ".tif",
    ".tiff",
    ".p7s",
    ".pdf",
    ".zip",
    ".rar",
    ".sql",
}


def validate_file_extension(value):
    name = getattr(value, "name", "")
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_FILE_EXTENSIONS:
        raise ValidationError(f"Недопустимый формат файла: {ext}")


def validate_file_size(value):
    max_size = 50 * 1024 * 1024  # 50 MB
    if value.size > max_size:
        raise ValidationError("Файл превышает максимальный размер в 50 МБ.")


def validate_image_or_pdf(value):
    name = getattr(value, "name", "")
    ext = os.path.splitext(name)[1].lower()
    allowed = {".pdf", ".jpg", ".jpeg", ".png", ".bmp", ".gif", ".tif", ".tiff", ".webp"}
    if ext not in allowed:
        raise ValidationError(f"Допустимы только изображения и PDF. Получен формат: {ext}")