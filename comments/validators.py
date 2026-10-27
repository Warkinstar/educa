import os
from django.core.exceptions import ValidationError

MAX_COMMENT_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

ALLOWED_COMMENT_EXTENSIONS = {
    # Документы и таблицы
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.txt', '.rtf', '.odt',
    # Изображения
    '.png', '.jpg', '.jpeg', '.gif', '.webp',
    # Архивы
    '.zip', '.rar', '.7z', '.tar', '.gz'
}

DISALLOWED_EXTENSIONS = {
    '.exe', '.bat', '.sh', '.bin', '.cmd', '.msi', '.ps1', '.vbs', '.js', '.py'
}


def validate_comment_file(file_obj):
    if file_obj.size > MAX_COMMENT_FILE_SIZE:
        raise ValidationError("Размер файла не должен превышать 10 МБ.")

    ext = os.path.splitext(file_obj.name)[1].lower()
    if ext in DISALLOWED_EXTENSIONS or ext not in ALLOWED_COMMENT_EXTENSIONS:
        raise ValidationError(
            f"Недопустимый формат файла ({ext}). Разрешены документы, архивы и изображения."
        )