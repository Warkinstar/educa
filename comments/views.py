from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_http_methods, require_POST

from courses.models import Module
from .forms import CommentForm
from .models import Comment, CommentFile

from .tasks import send_new_comment_notification


def get_module_comments_queryset(module):
    content_type = ContentType.objects.get_for_model(Module)
    return (
        Comment.objects.filter(
            content_type=content_type,
            object_id=module.id,
            parent__isnull=True
        )
        .select_related('user')
        .prefetch_related('files', 'replies__user', 'replies__files')
        .order_by('-created_at')
    )


@login_required
@require_http_methods(["GET"])
def module_comments_list(request, module_public_id):
    module = get_object_or_404(Module, public_id=module_public_id)
    comments = get_module_comments_queryset(module)
    form = CommentForm()
    return render(
        request,
        'comments/partials/comments_container.html',
        {
            'module': module,
            'comments': comments,
            'form': form,
        }
    )


@login_required
@require_POST
def add_module_comment(request, module_public_id):
    module = get_object_or_404(Module, public_id=module_public_id)
    parent_id = request.POST.get('parent_id')
    parent = None
    if parent_id:
        parent = get_object_or_404(Comment, id=parent_id)

    form = CommentForm(request.POST, request.FILES)
    if form.is_valid():
        content_type = ContentType.objects.get_for_model(Module)
        comment = form.save(commit=False)
        comment.user = request.user
        comment.content_type = content_type
        comment.object_id = module.id
        comment.parent = parent
        comment.save()

        # Прикрепление файлов
        files = request.FILES.getlist('files')
        for f in files:
            CommentFile.objects.create(comment=comment, file=f)

        # Асинхронное уведомление преподавателя
        send_new_comment_notification.delay(comment.id)

        # Возвращаем обновленный контейнер комментариев
        comments = get_module_comments_queryset(module)
        new_form = CommentForm()
        response = render(
            request,
            'comments/partials/comments_container.html',
            {
                'module': module,
                'comments': comments,
                'form': new_form,
            }
        )
        response['HX-Trigger'] = '{"showToast": "Комментарий успешно добавлен"}'
        return response

    comments = get_module_comments_queryset(module)
    return render(
        request,
        'comments/partials/comments_container.html',
        {
            'module': module,
            'comments': comments,
            'form': form,
        },
        status=400
    )


@login_required
@require_POST
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment, id=comment_id)
    if comment.user != request.user and not request.user.is_staff:
        return HttpResponseForbidden("У вас нет прав на удаление этого комментария.")

    comment.is_deleted = True
    comment.text = "Сообщение удалено автором."
    comment.save(update_fields=['is_deleted', 'text'])

    module = comment.content_object
    comments = get_module_comments_queryset(module)
    form = CommentForm()
    response = render(
        request,
        'comments/partials/comments_container.html',
        {
            'module': module,
            'comments': comments,
            'form': form,
        }
    )
    response['HX-Trigger'] = '{"showToast": "Комментарий удален"}'
    return response