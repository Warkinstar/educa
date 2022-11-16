from django.shortcuts import render
from accounts.forms import CustomUserCreationForm
from django.views.generic import CreateView
from .forms import CustomUserCreationForm, CourseEnrollForm
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin


class UserRegistrationView(CreateView):
    template_name = "accounts/registration.html"
    form_class = CustomUserCreationForm
    success_url = reverse_lazy("student_course_list")

    def form_valid(self, form):
        result = super().form_valid(form)
        cd = form.cleaned_data
        user = authenticate(
            username=cd["username"],
            password=cd["password1"],
            )
        login(self.request, user)
        return result


class StudentEnrollCourseView(LoginRequiredMixin, FormView):
    form_class = CourseEnrollForm
    course = None

    def form_valid(self, form):
        self.course = form.cleaned_data["course"]
        self.course.students.add(self.request.user)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy("student_course_detail", args=[self.course.id])

