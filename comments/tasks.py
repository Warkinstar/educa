from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Comment


@shared_task
def send_new_comment_notification(comment_id):
    try:
        comment = Comment.objects.select_related('user').get(id=comment_id)
        module = comment.content_object
        course = module.course
        instructor = course.owner

        # Не отправляем письмо, если автор комментария и есть преподаватель
        if comment.user == instructor or not instructor.email:
            return

        subject = f"Новый комментарий к модулю: {module.title}"
        message = (
            f"Пользователь {comment.user.get_full_name() or comment.user.username} "
            f"оставил новый комментарий в модуле «{module.title}» курса «{course.title}»:\n\n"
            f"«{comment.text}»\n\n"
            f"Ответить на комментарий вы можете в личном кабинете."
        )

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@educa.local',
            recipient_list=[instructor.email],
            fail_silently=False,
        )
    except Comment.DoesNotExist:
        pass