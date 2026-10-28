import logging
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.mail import get_connection
from django.utils import timezone


logger = logging.getLogger(__name__)
User = get_user_model()


def get_smtp_connection(smtp_alias="default"):
    """
    Возвращает экземпляр email backend соединения по алиасу из settings.EMAIL_BACKENDS.
    По умолчанию используется консольный бэкенд.
    """
    backends = getattr(settings, "EMAIL_BACKENDS", {})
    cfg = backends.get(smtp_alias) or backends.get("default", {})

    return get_connection(
        backend=cfg.get("BACKEND", "django.core.mail.backends.console.EmailBackend"),
        host=cfg.get("HOST", "smtp.gmail.com"),
        port=cfg.get("PORT", 587),
        username=cfg.get("USERNAME", ""),
        password=cfg.get("PASSWORD", ""),
        use_tls=cfg.get("USE_TLS", True),
        use_ssl=cfg.get("USE_SSL", False),
    )


def get_module_notify_users(module):
    """
    Возвращает QuerySet уникальных пользователей для уведомлений модуля:
    - автор курса;
    - студенты на самозаписи;
    - студенты с активными назначениями (с учетом дат начала и дедлайна);
    - все пользователи, оставлявшие комментарии к данному модулю.
    Число запросов к БД константно (без N+1).
    """
    from comments.models import Comment

    course = module.course
    now = timezone.now()

    # 1. Автор курса
    owner_id = course.owner_id

    # 2. Студенты на самозаписи
    enrolled_ids = list(course.students.values_list("id", flat=True))

    # 3. Студенты с действующими назначениями
    assignments_qs = (
        course.assignments.filter(is_active=True).filter(activated_at__isnull=True)
        | course.assignments.filter(
            is_active=True, activated_at__lte=now, due_date__isnull=True
        )
        | course.assignments.filter(
            is_active=True, activated_at__lte=now, due_date__gte=now
        )
    )
    assigned_ids = list(assignments_qs.values_list("user_id", flat=True))

    # 4. Пользователи, оставлявшие комментарии к модулю
    module_ct = ContentType.objects.get_for_model(module)
    commenter_ids = list(
        Comment.objects.filter(
            content_type=module_ct,
            object_id=str(module.id),
        ).values_list("created_by_id", flat=True)
    )

    all_ids = {owner_id, *enrolled_ids, *assigned_ids, *commenter_ids} - {None}

    return User.objects.filter(id__in=all_ids).order_by("first_name", "last_name", "username")


def send_comment_notifications(
    comment,
    subject,
    message_text,
    comment_page_link,
    users,
    smtp_alias="default",
):
    """Уведомляет участников о новом комментарии асинхронно через Celery."""
    from .tasks import send_comment_notification_email_task

    if getattr(comment, "created_by", None):
        comment_author = comment.created_by.get_full_name() or comment.created_by.username
    elif getattr(comment, "user", None):
        comment_author = comment.user.get_full_name() or comment.user.username
    else:
        meta = getattr(comment, "metadata", None) or {}
        comment_author = meta.get("name", "-") if isinstance(meta, dict) else "-"

    for user in users:
        email = None
        user_name = ""

        if isinstance(user, str):
            email = user
        elif user and getattr(user, "email", None):
            email = user.email
            user_name = user.get_full_name() or user.username

        if not email:
            continue

        try:
            send_comment_notification_email_task.delay(
                email=email,
                user_name=user_name,
                comment_author=comment_author,
                subject=subject,
                message_text=message_text,
                comment_page_link=comment_page_link,
                smtp_alias=smtp_alias,
            )
        except Exception as exc:
            logger.exception("Не удалось поставить в очередь отправку email на %s: %s", email, exc)