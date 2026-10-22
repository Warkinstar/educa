from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic.edit import CreateView
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import UpdateView, DeleteView
from .forms import CustomUserCreationForm, CourseEnrollForm
from django.urls import reverse_lazy, reverse
from django.db.models import Prefetch, Q
from django.contrib.auth import authenticate, login
from django.views.generic import FormView
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from .models import StudentAnswer
from courses.models import Course, Task, Content, CourseAssignment
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.contrib import messages



class UserRegistrationView(CreateView):
    template_name = "accounts/registration.html"
    form_class = CustomUserCreationForm

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
        user = self.request.user

        # 1. Загружаем активные назначения пользователя заранее через Prefetch
        user_assignments_qs = (
            CourseAssignment.objects.filter(user=user, is_active=True)
            .select_related("group_assignment__group")
            .order_by("-assigned_at")
        )

        # 2. Выбираем только активные курсы, к которым есть доступ:
        # либо пользователь в students, либо есть активное назначение
        qs = (
            Course.objects.filter(is_active=True)
            .filter(
                Q(students=user) | Q(assignments__in=user_assignments_qs)
            )
            .distinct()
            .prefetch_related(
                Prefetch(
                    "assignments",
                    queryset=user_assignments_qs,
                    to_attr="user_assignments",
                )
            )
        )

        courses = list(qs)
        now = timezone.now()

        # 3. Вычисляем статус, дедлайн и источник для каждого курса
        for course in courses:
            assignments = getattr(course, "user_assignments", [])
            if assignments:
                assignment = assignments[0]
                course.assignment_due_date = assignment.due_date
                course.assignment_activated_at = assignment.activated_at

                # Источник назначения
                if assignment.group_assignment and assignment.group_assignment.group:
                    course.assignment_source = f"Группа: {assignment.group_assignment.group.name}"
                else:
                    course.assignment_source = "Назначено лично"

                # Статус доступа по датам
                if assignment.activated_at and assignment.activated_at > now:
                    course.assignment_status = "scheduled"
                    local_act = timezone.localtime(assignment.activated_at)
                    course.assignment_status_display = f"Откроется {local_act.strftime('%d.%m.%Y')}"
                    course.can_open = False
                elif assignment.due_date and assignment.due_date < now:
                    course.assignment_status = "expired"
                    course.assignment_status_display = "Срок истёк"
                    course.can_open = False
                else:
                    course.assignment_status = "available"
                    course.assignment_status_display = "Доступен"
                    course.can_open = True
            else:
                # Если доступ получен через прямую запись (students)
                course.assignment_source = "Самозапись"
                course.assignment_status = "available"
                course.assignment_status_display = "Доступен"
                course.assignment_due_date = None
                course.assignment_activated_at = None
                course.can_open = True
                course.can_unsubscribe = True

        return courses


@login_required
def unsubscribe_course(request, course_pk):
    """Выполняет удаление request.user из course.students и деактивацию личных назначений"""
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        course = get_object_or_404(Course, pk=course_pk)
        has_active_assignment = CourseAssignment.objects.filter(
            course=course,
            user=request.user,
            is_active=True,
        ).exists()
        if not has_active_assignment and course.students.filter(pk=request.user.pk).exists():
            course.students.remove(request.user)
            return JsonResponse({"status": "success"})
        return JsonResponse({"status": "error", "message": "Нельзя отписаться от назначенного курса"}, status=400)
    return HttpResponse()  # Возвращаем пустой ответ


class StudentCourseDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = Course
    template_name = "accounts/course/detail.html"

    def test_func(self):
        """Проверка доступа через единый метод модели can_user_access"""
        obj = self.get_object()
        can_access, reason = obj.can_user_access(self.request.user)
        self.access_denied_reason = reason
        return can_access

    def handle_no_permission(self):
        from django.contrib import messages
        from django.shortcuts import redirect
        reason = getattr(self, "access_denied_reason", "У вас нет доступа к этому курсу.")
        messages.error(self.request, reason)
        return redirect("student_course_list")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        context["now"] = timezone.now()
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

    def dispatch(self, request, *args, **kwargs):
        """Определим переменные"""
        self.task = get_object_or_404(Task, id=self.kwargs["task_id"])
        # Content->Module посредством передачи имени модели и pk объекта
        self.module = Content.objects.get(
            content_type__model="task", object_id=self.task.pk
        ).module
        self.course = self.module.course  # Получить Course через Task
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Если пользователь отвечал на это задание, то запретить отвечать снова."""
        user = self.request.user
        # Если пользователь отвечал на вопрос - False
        if user.task_answers.filter(task=self.task):
            return False
        # Если не истек deadline False
        if self.task.deadline:
            if self.task.deadline < timezone.now():
                return False
        # Если пользователь есть в списке студентов курса
        if user in self.course.students.all():
            return True
        return False

    def form_valid(self, form):
        form.instance.task_id = self.kwargs["task_id"]
        form.instance.student = self.request.user
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["task"] = self.task
        context["module"] = self.module
        context["course"] = self.course
        return context

    def get_success_url(self):
        """Вернуться на страницу модулей и контентов"""
        return reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )


class StudentAnswerUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = StudentAnswer
    pk_url_kwarg = "answer_pk"
    fields = ["title", "content", "file"]
    template_name = "accounts/course/answer_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        self.answer = get_object_or_404(StudentAnswer, pk=self.kwargs["answer_pk"])
        # Получение Content->Model, передав имя модели и pk объекта
        self.module = get_object_or_404(
            Content, content_type__model="task", object_id=self.task.pk
        ).module
        self.course = self.module.course
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        user = self.request.user
        if self.task.deadline:
            if self.task.deadline < timezone.now():
                return False
        if self.answer.score:
            return False
        if user in self.course.students.all() and self.answer.student == user:
            return True
        return False

    def get_context_data(self, **kwargs):
        context = super().get_context_data()
        context["task"] = self.task
        context["module"] = self.module
        context["course"] = self.course
        return context

    def get_success_url(self):
        return reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )


class StudentAnswerDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = StudentAnswer
    pk_url_kwarg = "answer_pk"
    template_name = "accounts/course/answer_delete.html"

    def dispatch(self, request, *args, **kwargs):
        # Получение Conten->Model, передав имя модели и его pk
        self.module = get_object_or_404(
            Content, content_type__model="task", object_id=self.kwargs["task_pk"]
        ).module
        self.course = self.module.course
        self.answer = self.get_object()
        self.task = self.answer.task
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        user = self.request.user
        if self.task.deadline:
            if self.task.deadline < timezone.now():
                return False
        if user in self.course.students.all() and self.answer.student == user:
            return True
        return False

    def get_success_url(self):
        return reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )


class StudentAnswerDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    model = StudentAnswer
    context_object_name = "answer"
    template_name = "accounts/course/answer_detail.html"

    def dispatch(self, request, *args, **kwargs):
        self.answer = self.get_object()
        self.task = self.answer.task
        # Content->Module
        self.module = Content.objects.get(
            content_type__model="task", object_id=self.task.pk
        ).module
        self.course = self.module.course
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
        context["module"] = self.module
        context["course"] = self.course
        return context

    def test_func(self):
        if self.answer.student == self.request.user:
            return True
        return False