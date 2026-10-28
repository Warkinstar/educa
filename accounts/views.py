# Standard library
import uuid


# Django
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.db.models import Count, Prefetch, Q, prefetch_related_objects
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views import View
from django.views.decorators.http import require_POST
from django.views.generic import FormView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView


# Other project applications
from comments.forms import CommentForm
from comments.utils import get_module_notify_users
from courses.models import Course, Content, CourseAssignment, CourseProgress, Task
from courses.progress_service import (
    can_open_module,
    complete_module,
    ensure_course_started,
    get_course_progress_percent,
    get_module_unpassed_quizzes,
    get_modules_state,
    select_default_module_state,
    select_next_open_module,
    select_redirect_module_state,
    calculate_progress,
)


# Current application: accounts
from .forms import CourseEnrollForm, CustomUserCreationForm
from .models import StudentAnswer



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

        # 1. Загружаем активные назначения и прогресс пользователя заранее через Prefetch
        user_assignments_qs = (
            CourseAssignment.objects.filter(user=user, is_active=True)
            .select_related("group_assignment__group")
            .order_by("-assigned_at")
        )
        user_progress_qs = CourseProgress.objects.filter(user=user)
        accessible_courses = Course.objects.filter(
            Q(students=user) | Q(assignments__user=user, assignments__is_active=True)
        ).values("pk")

        # 2. Выбираем только активные курсы, к которым есть доступ:
        # либо пользователь в students, либо есть активное назначение.
        # Предзагружаем число модулей и пройденных модулей без N+1.
        qs = (
            Course.objects.filter(is_active=True, pk__in=accessible_courses)
            .annotate(
                total_modules=Count("modules", distinct=True),
                completed_modules=Count(
                    "modules",
                    filter=Q(modules__user_progresses__user=user),
                    distinct=True,
                ),
            )
            .prefetch_related(
                Prefetch(
                    "assignments",
                    queryset=user_assignments_qs,
                    to_attr="user_assignments",
                ),
                Prefetch(
                    "user_progresses",
                    queryset=user_progress_qs,
                    to_attr="user_course_progresses",
                ),
            )
        )

        courses = list(qs)
        now = timezone.now()

        # 3. Вычисляем статус, дедлайн, источник и прогресс для каждого курса
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

            progress_list = getattr(course, "user_course_progresses", [])
            course_progress = progress_list[0] if progress_list else None
            completed_at = course_progress.completed_at if course_progress else None

            total_modules = course.total_modules or 0
            completed_modules = course.completed_modules or 0

            course.total_modules = total_modules
            course.completed_modules = completed_modules
            course.completed_at = completed_at
            course.progress_percent, course.is_completed = calculate_progress(
                total_modules,
                completed_modules,
                has_completed_at=(completed_at is not None),
            )

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

    def get_object(self, queryset=None):
        if not hasattr(self, "_course_obj"):
            self._course_obj = super().get_object(queryset=queryset)
        return self._course_obj

    def test_func(self):
        """Проверка доступа через единый метод модели can_user_access"""
        obj = self.get_object()
        can_access, reason = obj.can_user_access(self.request.user)
        self.access_denied_reason = reason
        return can_access

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        reason = getattr(self, "access_denied_reason", None) or "У вас нет доступа к этому курсу."
        messages.error(self.request, reason)
        return redirect("student_course_list")

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        course = self.object

        # Фиксируем старт курса при первом открытии студентом (автор пропускается)
        ensure_course_started(course, request.user)

        self.modules_state = get_modules_state(course, request.user)
        states_by_module_id = {
            state["module"].pk: state for state in self.modules_state
        }

        if "module_id" in self.kwargs:
            try:
                module_id = int(self.kwargs["module_id"])
            except (TypeError, ValueError) as exc:
                raise Http404("Модуль не найден") from exc

            requested_module = get_object_or_404(course.modules, id=module_id)
            target_state = states_by_module_id.get(requested_module.pk)

            if target_state is None or not target_state["is_open"]:
                lock_reason = (
                    target_state["lock_reason"]
                    if target_state and target_state["lock_reason"]
                    else "Модуль закрыт для прохождения."
                )
                messages.warning(request, lock_reason)
                fallback_state = select_redirect_module_state(self.modules_state)
                if fallback_state is not None:
                    return redirect(
                        "student_course_detail_module",
                        pk=course.pk,
                        module_id=fallback_state["module"].pk,
                    )
                return redirect("student_course_detail", pk=course.pk)

            self.current_module_state = target_state
        else:
            self.current_module_state = select_default_module_state(self.modules_state)

        context = self.get_context_data(object=self.object)
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        course = self.get_object()
        modules_state = getattr(self, "modules_state", None)
        if modules_state is None:
            modules_state = get_modules_state(course, self.request.user)
        current_state = getattr(self, "current_module_state", None)
        current_module = current_state["module"] if current_state else None
        context["now"] = timezone.now()
        context["modules_state"] = modules_state
        context["current_module_state"] = current_state
        context["module"] = current_module
        context["unpassed_quizzes"] = (
            get_module_unpassed_quizzes(current_module, self.request.user)
            if current_module is not None
            else []
        )
        context["course_progress_percent"] = get_course_progress_percent(
            course, self.request.user
        )
        # Контекст для универсальных комментариев модуля
        if current_module:
            prefetch_related_objects(
                [current_module],
                "comments__files",
                "comments__created_by",
                "comments__reply_to__created_by",
                "comments__mention",
            )
            upload_session_id = uuid.uuid4()
            context["target_instance"] = current_module
            context["upload_session_id"] = upload_session_id
            context["comment_form"] = CommentForm(initial={"upload_session_id": upload_session_id})
            context["notify_users"] = get_module_notify_users(current_module)
        return context

class ModuleCompleteView(LoginRequiredMixin, View):
    """Завершение модуля студентом через сервисный слой прогресса."""

    def post(self, request, pk, module_id, *args, **kwargs):
        course = get_object_or_404(Course, pk=pk)
        module = get_object_or_404(course.modules, id=module_id)

        try:
            complete_module(module, request.user)
        except ValidationError as exc:
            error_message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            messages.error(request, error_message)

            has_access, _ = course.can_user_access(request.user)
            if not has_access:
                return redirect("student_course_list")

            is_open, _ = can_open_module(module, request.user)
            if is_open:
                return redirect(
                    "student_course_detail_module",
                    pk=course.pk,
                    module_id=module.pk,
                )
            return redirect("student_course_detail", pk=course.pk)

        messages.success(request, f"Модуль «{module.title}» успешно пройден.")
        next_module = select_next_open_module(course, request.user, module)
        if next_module is not None:
            return redirect(
                "student_course_detail_module",
                pk=course.pk,
                module_id=next_module.pk,
            )
        return redirect("student_course_detail", pk=course.pk)


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