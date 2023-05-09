from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden, JsonResponse
from django.contrib.auth.decorators import login_required
from courses.models import Course
from .models import Message
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin
from django.contrib.auth.decorators import user_passes_test
from el_pagination.views import AjaxListView


class ChatMessageListView(LoginRequiredMixin, UserPassesTestMixin, AjaxListView):
    """List message of course_id"""

    template_name = "chat/room.html"
    page_template = "chat/message_list_page.html"
    context_object_name = "messages"

    def test_func(self):
        """Check request.user in course.students"""
        # prefetch related course-messages
        self.course = Course.objects.prefetch_related("messages", "modules").get(
            pk=self.kwargs["course_id"]
        )
        return self.course.students.filter(pk=self.request.user.pk).exists()

    def get_queryset(self):
        """Messages of course"""
        # 50 сообщений от новых к старым
        return self.course.messages.all().order_by("-created")[:50]

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["course"] = self.course
        return context


@login_required
def message_delete(request, course_id, message_pk):
    """Функция удаления сообщения"""
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        # check that request.user == course.onwer
        course = get_object_or_404(Course, pk=course_id, owner=request.user)
        message = get_object_or_404(Message, pk=message_pk)
        message.delete()
        return JsonResponse({"status": "success"})
