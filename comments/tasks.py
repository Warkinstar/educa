import logging
from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def send_comment_notification_email_task(
    self,
    email,
    user_name,
    comment_author,
    subject,
    message_text,
    comment_page_link,
):
    """Фоновая отправка одного email-уведомления о комментарии."""
    context = {
        "user_name": user_name,
        "comment_author": comment_author,
        "subject": subject,
        "comment_text": message_text,
        "document_url": comment_page_link,
    }

    try:
        html_message = render_to_string("comments/comment_notification.html", context)
        send_mail(
            subject=f"{subject}",
            message=message_text,
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "noreply@educa.local"),
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Ошибка при отправке email на %s: %s", email, exc)
        raise self.retry(exc=exc, countdown=60)