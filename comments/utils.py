import logging
from .tasks import send_comment_notification_email_task

logger = logging.getLogger(__name__)


def send_comment_notifications(
    comment,
    subject,
    message_text,
    comment_page_link,
    users,
    smtp_alias="default",
):
    """Уведомляет участников о новом комментарии асинхронно через Celery."""
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
            )
        except Exception as exc:
            logger.exception("Не удалось поставить в очередь отправку email на %s: %s", email, exc)