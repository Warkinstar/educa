import uuid
from datetime import timedelta

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.views.generic.base import View
from django_htmx.http import reswap, retarget

from comments.forms import CommentForm
from comments.models import Comment, CommentFile
from comments.utils import send_comment_notifications


class UnrelatedCommentFileUploadView(LoginRequiredMixin, View):
    """Сохранение временных файлов до отправки комментария."""

    def post(self, request, *args, **kwargs):
        uploaded_file = request.FILES.get("file")
        upload_session_id = request.POST.get("upload_session_id")

        if not upload_session_id or not uploaded_file:
            return JsonResponse({"status": "error", "message": "Нет файла в запросе или токена"}, status=400)

        comment_file = CommentFile(
            file=uploaded_file,
            upload_session_id=upload_session_id,
            filename=uploaded_file.name,
            created_by=request.user,
        )
        comment_file.save()

        return JsonResponse({"status": "ok", "file_path": comment_file.file.url})


class UnrelatedCommentFileListView(LoginRequiredMixin, View):
    """Список файлов текущей upload-сессии."""

    def dispatch(self, request, *args, **kwargs):
        self.upload_session_id = request.GET.get("upload_session_id")
        self.unrelated_comment_files = CommentFile.objects.filter(
            upload_session_id=self.upload_session_id
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return render(
            request,
            "comments/unrelated_comment_files_form_info.html",
            {
                "unrelated_comment_files": self.unrelated_comment_files,
                "upload_session_id": self.upload_session_id,
            },
        )


class UnrelatedCommentFileDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Удаление временного файла из сессии."""

    def test_func(self):
        return self.unrelated_comment_file.created_by == self.request.user or self.request.user.is_superuser

    def dispatch(self, request, *args, **kwargs):
        self.unrelated_comment_file = get_object_or_404(
            CommentFile,
            public_id=self.kwargs.get("public_id"),
        )
        self.upload_session_id = self.unrelated_comment_file.upload_session_id
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.unrelated_comment_file.delete()
        return render(
            request,
            "comments/unrelated_comment_file_delete.html",
            {"upload_session_id": self.upload_session_id},
        )


class CommentCreateView(LoginRequiredMixin, View):
    """Создание комментария к любому объекту модели."""

    def get_target_instance(self):
        return get_object_or_404(
            self.model.objects.prefetch_related(
                "comments__files",
                "comments__created_by",
                "comments__reply_to__created_by",
                "comments__mention",
            ),
            public_id=self.public_id,
        )

    def dispatch(self, request, *args, **kwargs):
        self.app_label = self.kwargs.get("app_label")
        self.model_name = self.kwargs.get("model_name")
        self.public_id = self.kwargs.get("public_id")
        self.model = apps.get_model(app_label=self.app_label, model_name=self.model_name)
        self.target_instance = self.get_target_instance()
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        comment_form = CommentForm(data=request.POST)
        upload_session_id = self.request.POST.get("upload_session_id")

        if comment_form.is_valid():
            comment = comment_form.save(commit=False)
            comment.content_object = self.target_instance
            comment.created_by = request.user
            comment.save()

            session_id = comment_form.cleaned_data.get("upload_session_id")
            if session_id:
                CommentFile.bind_files_to_comment(session_id, comment)

            notify_reply_to = comment_form.cleaned_data.get("notify_reply_to", False)
            notify_participants = comment_form.cleaned_data.get("notify_participants", False)

            next_upload_session_id = uuid.uuid4()
            fresh_comment_form = CommentForm(initial={"upload_session_id": next_upload_session_id})

            subject = request.POST.get("comment_subject") or "Новое сообщение"
            message_text = request.POST.get("comment_message") or comment.text
            user_ids = request.POST.getlist("comment_notify_users", [])

            users = []
            if (notify_reply_to and comment.reply_to) or (notify_reply_to and comment.mention):
                users.append(comment.mention or comment.reply_to.created_by)

            if notify_participants and user_ids:
                users = list(get_user_model().objects.filter(pk__in=user_ids))

            comment_page_link = request.POST.get("comment_page_link")

            comment.metadata = {
                **(comment.metadata or {}),
                "notifications": {
                    "notify_reply_to": bool(notify_reply_to),
                    "notify_participants": bool(notify_participants),
                    "notified_user_ids": [u.pk for u in users if hasattr(u, "pk")],
                },
            }
            comment.save(update_fields=["metadata"])

            send_comment_notifications(
                comment=comment,
                subject=subject,
                message_text=message_text,
                comment_page_link=comment_page_link,
                users=users,
            )

            context = {
                "target_instance": self.get_target_instance(),
                "comment_form": fresh_comment_form,
                "upload_session_id": next_upload_session_id,
            }
            return render(request, "comments/comments_and_form_section.html", context)

        unrelated_comment_files = CommentFile.objects.filter(upload_session_id=upload_session_id)
        context = {
            "target_instance": self.target_instance,
            "comment_form": comment_form,
            "upload_session_id": upload_session_id,
            "unrelated_comment_files": unrelated_comment_files,
        }

        response = render(request, "comments/comment_form.html", context)
        retarget(response, f"#comment-form-{self.target_instance.public_id}")
        reswap(response, "outerHTML")
        return response


class CommentDeleteView(LoginRequiredMixin, UserPassesTestMixin, View):
    """Удаление комментария (только суперюзер или автор в течение 3 часов)."""

    def test_func(self):
        comment = self.comment
        if self.request.user.is_superuser:
            return True
        if self.request.user == comment.created_by and timezone.now() - comment.created <= timedelta(hours=3):
            return True
        return False

    def dispatch(self, request, *args, **kwargs):
        self.comment = get_object_or_404(Comment, public_id=self.kwargs.get("public_id"))
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.comment.delete()
        return HttpResponse("")


class CommentFileDownloadView(LoginRequiredMixin, View):
    """Скачивание файла комментария."""

    def dispatch(self, request, *args, **kwargs):
        self.comment_file = get_object_or_404(
            CommentFile.objects.select_related("comment"),
            public_id=self.kwargs.get("public_id"),
        )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        verbose_filename = self.comment_file.filename or self.comment_file._filename
        return FileResponse(
            self.comment_file.file.open("rb"),
            as_attachment=True,
            filename=verbose_filename,
        )