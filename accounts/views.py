from django.shortcuts import render, get_object_or_404
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from .forms import CustomUserCreationForm, CourseEnrollForm
from django.urls import reverse_lazy, reverse
from django.contrib.auth import authenticate, login
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from courses.models import Course, Task, Content
from .models import StudentAnswer


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


class StudentCourseListView(LoginRequiredMixin, ListView):
    model = Course
    template_name = "accounts/course/list.html"

    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(students__in=[self.request.user])


class StudentCourseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Course
    template_name = "accounts/course/detail.html"

    def test_func(self):
        """Доступ либо автору либо подписчику"""
        obj = self.get_object()
        if obj.owner == self.request.user:
            return True
        elif self.request.user in obj.students.all():
            return True

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        if "module_id" in self.kwargs:
            context["module"] = course.modules.get(id=self.kwargs["module_id"])
        else:
            if course.modules.all().count() > 0:
                context["module"] = course.modules.all()[0]
        return context


class StudentAnswerCreateView(LoginRequiredMixin, UserPassesTestMixin, CreateView):
    model = StudentAnswer
    fields = ["title", "content", "file"]
    template_name = "accounts/course/answer_form.html"
    success_url = "student_answer_detail"

    def test_func(self):
        """Если пользователь отвечал на это задание, то запретить отвечать снова."""
        task = get_object_or_404(Task, id=self.kwargs["task_id"])
        self.module = Content.objects.get(item_object=task).module
        self.course = self.module.course  # Получить Course через Task
        user = self.request.user

        # Если пользователь отвечал на вопрос - False
        if user.task_answers.filter(task=task):
            return False
        # Если пользователь есть в списке студентов курса
        if user in self.course.students.all():
            return True

    def form_valid(self, form):
        form.instance.task_id = self.kwargs["task_id"]
        form.instance.student = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        """Вернуться на страницу модулей и контентов"""
        return reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )


class StudentAnswerDetailView(DetailView):
    pass