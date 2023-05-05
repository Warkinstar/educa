from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from courses.models import Course
from .models import Message
from django.views.generic.list import ListView
from django.contrib.auth.mixins import UserPassesTestMixin, LoginRequiredMixin


class ChatMessageListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """List message of course_id"""

    template_name = "chat/room.html"
    context_object_name = "messages"

    def test_func(self):
        """Check request.user in course.students"""
        # prefetch related course-messages
        self.course = Course.objects.prefetch_related("messages").get(
            pk=self.kwargs["course_id"]
        )
        return self.course.students.filter(pk=self.request.user.pk).exists()

    def get_queryset(self):
        """Messages of course"""
        return self.course.messages.all()

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context["course"] = self.course
        return context
