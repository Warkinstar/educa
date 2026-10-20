import json
import os
from uuid import uuid4

from braces.views import CsrfExemptMixin, JsonRequestResponseMixin
from django.apps import apps
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q,  Avg, Count, Prefetch
from django.forms.models import inlineformset_factory, modelform_factory
from django.http import (
    HttpResponse,
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView

from accounts.forms import CourseEnrollForm
from accounts.models import StudentAnswer, StudentQuizResult
from chat.models import Message as ChatMessage
from orders.models import OrderItem

from . import forms
from .filters import CourseFilter
from .forms import (
    CourseModalForm,
    CourseModuleFormSet,
    CourseModuleInlineForm,
    SubjectForm,
)
from .mixins import QuerySetSearchMixin
from .models import (
    Answer,
    Content,
    Course,
    Module,
    Question,
    Quiz,
    Subject,
    Task,
)
from .widgets import DateTimePickerInput

User = get_user_model()


class ManageCourseListView(LoginRequiredMixin, PermissionRequiredMixin, QuerySetSearchMixin):
    template_name = "courses/manage/course/list.html"
    partial_template_name = "courses/manage/course/partials/partial_course_list.html"
    objects_per_page = 12
    filter = CourseFilter
    permission_required = "courses.view_course"

    def get_queryset(self):
        first_mod_prefetch = Prefetch(
            "modules",
            queryset=Module.objects.order_by("order", "id"),
            to_attr="prefetched_modules",
        )
        return (
            Course.objects.filter(owner=self.request.user)
            .select_related("subject", "owner")
            .prefetch_related(first_mod_prefetch)
            .annotate(
                total_modules=Count("modules", distinct=True),
                total_students=Count("students", distinct=True),
            )
            .order_by("-created")
        )

    def get_context_data(self):
        context = {}
        if not getattr(self.request, "htmx", False):
            context["user_subjects"] = (
                Subject.objects.filter(courses__owner=self.request.user)
                .annotate(courses_count=Count("courses", distinct=True))
                .order_by("title")
            )
        return context

    def get_filter_params(self, request):
        return {
            "subject": request.GET.getlist("subject"),
        }


# --- МОДАЛКИ КУРСА: СОЗДАНИЕ И РЕДАКТИРОВАНИЕ ---

class CourseCreateModalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ["courses.add_course"]

    def get(self, request, *args, **kwargs):
        form = CourseModalForm()
        module_formset = CourseModuleFormSet(prefix="modules")
        return render(request, "courses/manage/course/partials/course_create_form.html", {
            "form": form,
            "module_formset": module_formset,
        })

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        form = CourseModalForm(request.POST)
        module_formset = CourseModuleFormSet(request.POST, prefix="modules")

        if form.is_valid() and module_formset.is_valid():
            course = form.save(commit=False)
            course.owner = request.user
            course.save()
            form.save_m2m()

            module_formset.instance = course
            module_formset.save()

            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({
                "refreshPage": True,
                "showToast": f"Курс «{course.title}» успешно создан",
                "closeModal": "#modal-create-course",
            })
            return response

        return render(request, "courses/manage/course/partials/course_create_form.html", {
            "form": form,
            "module_formset": module_formset,
        }, status=422)


class CourseUpdateModalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    """Редактирование только полей курса (модули редактируются в отдельной модалке)"""
    permission_required = ["courses.change_course"]

    def get_course(self):
        return get_object_or_404(Course, id=self.kwargs.get("pk"), owner=self.request.user)

    def get(self, request, *args, **kwargs):
        course = self.get_course()
        form = CourseModalForm(instance=course)
        return render(request, "courses/manage/course/partials/course_update_form.html", {
            "form": form,
            "course": course,
        })

    def post(self, request, *args, **kwargs):
        course = self.get_course()
        form = CourseModalForm(request.POST, instance=course)
        if form.is_valid():
            course = form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({
                "refreshPage": True,
                "showToast": f"Курс «{course.title}» успешно сохранен",
                "closeModal": "#modal-update-course",
            })
            return response

        return render(request, "courses/manage/course/partials/course_update_form.html", {
            "form": form,
            "course": course,
        }, status=422)

# --- МОДАЛКА УДАЛЕНИЯ КУРСА СО СВОДКОЙ И ОЧИСТКОЙ GFK ---

class CourseDeleteModalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "courses.delete_course"

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs.get("pk"), owner=self.request.user)

    def get(self, request, *args, **kwargs):
        course = self.get_course()
        modules = course.modules.all()
        content_items = Content.objects.filter(module__in=modules).select_related("content_type")

        # Названия типов контента по-русски
        type_labels = {
            "text": "Тексты",
            "htmltext": "Тексты",
            "video": "Видео",
            "file": "Файлы",
            "image": "Изображения",
            "task": "Задания",
            "quiz": "Тесты",
        }

        content_counts = {}
        for c in content_items:
            ct_name = c.content_type.model.lower()
            label = type_labels.get(ct_name, ct_name.capitalize())
            content_counts[label] = content_counts.get(label, 0) + 1

        chat_messages_count = ChatMessage.objects.filter(course=course).count()
        order_items_count = OrderItem.objects.filter(module__in=modules).count()

        # Ответы студентов и результаты тестов
        student_answers_count = StudentAnswer.objects.filter(task__contents__module__in=modules).count()
        quiz_results_count = StudentQuizResult.objects.filter(quiz__contents__module__in=modules).count()

        context = {
            "course": course,
            "modules": modules,
            "content_counts": content_counts,
            "chat_messages_count": chat_messages_count,
            "order_items_count": order_items_count,
            "students_count": course.students.count(),
            "student_answers_count": student_answers_count,
            "quiz_results_count": quiz_results_count,
        }
        return render(request, "courses/manage/course/partials/course_delete_summary.html", context)

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        course = self.get_course()
        modules = course.modules.all()
        # Очищаем полиморфные объекты контента
        for content in Content.objects.filter(module__in=modules):
            if content.item:
                content.item.delete()

        title = course.title
        course.delete()

        response = HttpResponse("")
        response["HX-Trigger"] = json.dumps({
            "closeModal": "#modal-delete-course",
            "showToast": f"Курс «{title}» успешно удален",
            "refreshPage": True,
        })
        return response

# --- МОДАЛКА УПРАВЛЕНИЯ МОДУЛЯМИ КУРСА ---

class CourseModulesManageModalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "courses.change_course"

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs.get("pk"), owner=self.request.user)

    def get(self, request, *args, **kwargs):
        course = self.get_course()
        formset = forms.CourseModuleFormSet(instance=course, prefix="manage_modules")
        return render(request, "courses/manage/course/partials/course_modules_form.html", {
            "course": course,
            "formset": formset,
        })

    @transaction.atomic
    def post(self, request, *args, **kwargs):
        course = self.get_course()
        formset = forms.CourseModuleFormSet(request.POST, instance=course, prefix="manage_modules")
        if formset.is_valid():
            # Очищаем контент удаляемых модулей перед сохранением формсета
            for form in formset.deleted_forms:
                if form.instance.pk:
                    for content in Content.objects.filter(module=form.instance):
                        if content.item:
                            content.item.delete()

            formset.save()
            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({
                "closeModal": "#modal-manage-modules", "closeModalContent": "#modal-modules-course",
                "showToast": "Модули курса успешно обновлены",
                "refreshPage": True,
            })
            return response

        return render(request, "courses/manage/course/partials/course_modules_form.html", {
            "course": course,
            "formset": formset,
        }, status=422)

# --- МОДАЛКА СТУДЕНТОВ КУРСА И ИСКЛЮЧЕНИЕ ---

class CourseStudentsModalView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = "courses.change_course"

    def get_course(self):
        return get_object_or_404(Course, pk=self.kwargs.get("pk"), owner=self.request.user)

    def get(self, request, *args, **kwargs):
        course = self.get_course()
        form = forms.AddStudentsToCourseForm(course=course)
        return render(request, "courses/manage/course/partials/course_students_modal_body.html", {
            "course": course,
            "form": form,
        })

    def post(self, request, *args, **kwargs):
        from courses.assignment_service import assign_course_to_user
        course = self.get_course()
        form = forms.AddStudentsToCourseForm(request.POST, course=course)
        if form.is_valid():
            new_students = form.cleaned_data["students"]
            for student in new_students:
                try:
                    assign_course_to_user(course=course, user=student, assigned_by=request.user)
                except Exception:
                    pass
                course.students.add(student)
            response = render(request, "courses/manage/course/partials/course_students_modal_body.html", {
                "course": course,
                "form": forms.AddStudentsToCourseForm(course=course),
            })
            response["HX-Trigger"] = json.dumps({
                "showToast": "Студенты успешно добавлены и назначены на курс",
                "refreshPage": True,
            })
            return response

        return render(request, "courses/manage/course/partials/course_students_modal_body.html", {
            "course": course,
            "form": form,
        }, status=422)

@login_required
@require_POST
def exclude_student_from_course(request, course_pk, student_pk):
    if not request.user.has_perm("courses.change_course"):
        raise PermissionDenied
    course = get_object_or_404(Course, pk=course_pk, owner=request.user)
    student = get_object_or_404(User, pk=student_pk)
    course.students.remove(student)

    response = render(request, "courses/manage/course/partials/course_students_modal_body.html", {
        "course": course,
        "form": forms.AddStudentsToCourseForm(course=course),
    })
    response["HX-Trigger"] = json.dumps({
        "showToast": f"Студент {student.get_full_name() or student.username} исключен",
        "refreshPage": True,
    })
    return response


class SubjectCreateOffcanvasView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = ["courses.add_subject"]

    def get(self, request, *args, **kwargs):
        form = SubjectForm()
        return render(request, "courses/manage/course/partials/subject_create_form.html", {"form": form})

    def post(self, request, *args, **kwargs):
        form = SubjectForm(request.POST)
        if form.is_valid():
            subject = form.save()
            response = HttpResponse("")
            response["HX-Trigger"] = json.dumps({
                "showToast": f"Тема «{subject.title}» успешно создана",
                "closeCanvas": "#offcanvasRight",
            })
            return response

        return render(request, "courses/manage/course/partials/subject_create_form.html", {
            "form": form,
            "success": False,
        }, status=422)


class CourseModuleAddRowView(LoginRequiredMixin, View):
    def dispatch(self, request, *args, **kwargs):
        if not (request.user.has_perm("courses.add_course") or request.user.has_perm("courses.change_course")):
            return HttpResponseForbidden("Недостаточно прав.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        prefix = request.GET.get("modules_prefix", "modules")
        try:
            total_forms = int(request.GET.get(f"{prefix}-TOTAL_FORMS", 0))
        except (ValueError, TypeError):
            total_forms = 0

        form = CourseModuleInlineForm(prefix=f"{prefix}-{total_forms}")
        return render(request, "courses/manage/course/partials/module_form_row.html", {
            "form": form,
            "new_total": total_forms + 1,
            "modules_prefix": prefix,
        })


# --- УПРАВЛЕНИЕ КОНТЕНТОМ И ТЕСТАМИ ---

class ContentCreateUpdateView(TemplateResponseMixin, View):
    module = None
    model = None
    obj = None
    template_name = "courses/manage/content/form.html"

    def get_model(self, model_name):
        if model_name in ["htmltext", "text", "video", "image", "file", "task", "quiz"]:
            return apps.get_model(app_label="courses", model_name=model_name)
        return None

    def get_form(self, model, *args, **kwargs):
        Form = modelform_factory(
            model,
            exclude=["owner", "order", "created", "updated", "time", "difficulty"],
            widgets={"deadline": DateTimePickerInput()},
        )
        return Form(*args, **kwargs)

    def dispatch(self, request, module_id, model_name, id=None):
        self.module = get_object_or_404(
            Module, id=module_id, course__owner=request.user
        )
        self.model = self.get_model(model_name)
        if id:
            self.obj = get_object_or_404(self.model, id=id, owner=request.user)

        return super().dispatch(request, module_id, model_name, id)

    def get(self, request, module_id, model_name, id=None):
        form = self.get_form(self.model, instance=self.obj)
        return self.render_to_response(
            {"form": form, "object": self.obj, "module": self.module}
        )

    def post(self, request, module_id, model_name, id=None):
        form = self.get_form(
            self.model, instance=self.obj, data=request.POST, files=request.FILES
        )
        if form.is_valid():
            obj = form.save(commit=False)
            obj.owner = request.user
            obj.save()
            if not id:
                Content.objects.create(module=self.module, item=obj)
            return redirect("module_content_list", self.module.id)

        return self.render_to_response(
            {"form": form, "object": self.obj, "module": self.module}
        )


class CourseQuizQuestionAnswerCreateUpdateView(
    LoginRequiredMixin, UserPassesTestMixin, TemplateResponseMixin, View
):
    template_name = "courses/manage/quiz/quiz_manage_questions.html"

    def get_question_form(self, data=None):
        QuestionForm = modelform_factory(
            Question,
            fields=["text"],
        )
        return QuestionForm(instance=self.question_instance, data=data)

    def get_answer_inlineformset(self, data=None):
        num_of_answers = self.quiz.number_of_answers
        if self.question_instance:
            num_of_answers -= self.question_instance.answers.count()
        AnswerFormSet = inlineformset_factory(
            Question,
            Answer,
            fields=["text", "correct"],
            extra=num_of_answers,
            can_delete=False,
        )
        return AnswerFormSet(instance=self.question_instance, data=data)

    def dispatch(self, request, quiz_pk, question_pk=None):
        self.quiz = get_object_or_404(Quiz, id=quiz_pk)
        self.module = Content.objects.get(
            content_type__model="quiz", object_id=self.quiz.pk
        ).module
        self.course = self.module.course
        if question_pk:
            self.question_instance = get_object_or_404(
                Question, pk=question_pk, quiz=self.quiz
            )
        else:
            self.question_instance = None
        return super().dispatch(request, quiz_pk)

    def test_func(self):
        return self.course.owner == self.request.user

    def get(self, request, *args, **kwargs):
        question_form = self.get_question_form()
        answer_formset = self.get_answer_inlineformset()
        return self.render_to_response(
            {
                "quiz": self.quiz,
                "module": self.module,
                "question_form": question_form,
                "answer_formset": answer_formset,
            }
        )

    def post(self, request, *args, **kwargs):
        question_form = self.get_question_form(data=request.POST)
        answer_formset = self.get_answer_inlineformset(data=request.POST)
        if question_form.is_valid() and answer_formset.is_valid():
            question = question_form.save(commit=False)
            question.quiz = self.quiz
            question.save()
            answer_formset.instance = question
            answer_formset.save()
            if "add-another" in request.POST:
                return redirect("course_quiz_manage", quiz_pk=self.quiz.pk)
            return redirect("quizes:quiz-view", pk=self.quiz.pk)

        return self.render_to_response(
            {
                "quiz": self.quiz,
                "module": self.module,
                "question_form": question_form,
                "answer_formset": answer_formset,
            }
        )


def content_delete(request, module_pk, content_pk):
    if request.htmx:
        content = get_object_or_404(
            Content, pk=content_pk, module__course__owner=request.user
        )
        content.item.delete()
        content.delete()
        return HttpResponse("")

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        content = get_object_or_404(
            Content, pk=content_pk, module__course__owner=request.user
        )
        content.item.delete()
        content.delete()
        return JsonResponse({"status": "Content deleted successfully"})

def upload_image(request, module_id=None, model_name=None, id=None):
    if request.method != "POST":
        return JsonResponse({"Error Message": "Wrong request"})

    matching_module = get_object_or_404(
        Module, id=module_id, course__owner=request.user
    )

    file_obj = request.FILES["file"]
    file_name_suffix = file_obj.name.split(".")[-1]
    if file_name_suffix not in ["jpg", "png", "gif", "jpeg"]:
        return JsonResponse(
            {
                "Error Message": f"Wrong file suffix ({file_name_suffix}), supported qre .jpg, .png, .gif, jpeg"
            }
        )

    path = os.path.join(
        settings.MEDIA_ROOT,
        matching_module.course.slug + f"_id_{matching_module.course.id}",
        f"module_id_{matching_module.id}",
    )
    if not os.path.exists(path):
        os.makedirs(path)

    file_path = os.path.join(path, file_obj.name)
    if os.path.exists(file_path):
        file_obj.name = str(uuid4()) + "." + file_name_suffix
        file_path = os.path.join(path, file_obj.name)

    with open(file_path, "wb+") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

        return JsonResponse(
            {
                "message": "Image uploaded successfully",
                "location": os.path.join(
                    settings.MEDIA_URL,
                    matching_module.course.slug + f"_id_{matching_module.course.id}",
                    f"module_id_{matching_module.id}",
                    file_obj.name,
                ),
            }
        )

# --- УПРАВЛЕНИЕ ПОРЯДКОМ И СПИСКОМ КОНТЕНТА МОДУЛЯ ---

class ModuleContentListView(TemplateResponseMixin, View):
    template_name = "courses/manage/module/content_list.html"

    def get(self, request, module_id):
        module = get_object_or_404(Module, id=module_id, course__owner=request.user)
        return self.render_to_response({"module": module})


class ModuleOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Module.objects.filter(id=id, course__owner=request.user).update(order=order)
        return self.render_json_response({"saved": "OK"})


class ContentOrderView(CsrfExemptMixin, JsonRequestResponseMixin, View):
    def post(self, request):
        for id, order in self.request_json.items():
            Content.objects.filter(id=id, module__course__owner=request.user).update(
                order=order
            )
        return self.render_json_response({"saved": "OK"})


# --- ПУБЛИЧНЫЙ КАТАЛОГ КУРСОВ И ДЕТАЛИ ---

class CourseListView(QuerySetSearchMixin):
    model = Course
    filter = CourseFilter
    template_name = "courses/course/list.html"
    partial_template_name = "courses/course/partials/partial_course_list.html"
    objects_per_page = 6

    def get_filter_params(self, request):
        return {"subject": request.GET.getlist("subject")}

    def get_queryset(self):
        qs = self.model.objects.visible_to_students().annotate(
            total_modules=Count("modules")
        ).select_related("owner", "subject").order_by("-created")

        subject_slug = self.kwargs.get("subject")
        if subject_slug:
            qs = qs.filter(subject__slug=subject_slug)

        teacher_pk = self.kwargs.get("teacher_pk")
        if teacher_pk:
            qs = qs.filter(owner_id=teacher_pk)

        return qs

    def get_context_data(self, **kwargs):
        context = {}
        if not getattr(self.request, "htmx", False):
            context["subjects"] = Subject.objects.annotate(total_courses=Count("courses"))

        selected_list = self.request.GET.getlist("subject")
        context["selected_subjects_list"] = selected_list

        subject_slug = self.kwargs.get("subject")
        if not subject_slug:
            if len(selected_list) == 1:
                subject_slug = selected_list[0]
        if subject_slug:
            subject_obj = Subject.objects.filter(slug=subject_slug).first()
            context["subject"] = subject_obj
            context["current_subject"] = subject_obj
        else:
            context["subject"] = None
            context["current_subject"] = None

        return context


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course/detail.html"

    def get_queryset(self):
        # Автор всегда видит свой курс, остальные — только видимые студентам
        if self.request.user.is_authenticated:
            return Course.objects.filter(
                Q(owner=self.request.user) |
                (Q(is_active=True) & Q(is_public=True))
            ).distinct()
        return Course.objects.visible_to_students()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enroll_form"] = CourseEnrollForm(initial={"course": self.object})
        return context


# --- ЗАДАНИЯ И РЕЗУЛЬТАТЫ СТУДЕНТОВ ---

class TaskDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Задание и список ответов"""
    model = Task
    pk_url_kwarg = "task_pk"
    context_object_name = "task"
    template_name = "courses/manage/task/task_detail.html"

    def test_func(self):
        obj = self.get_object()
        return obj.owner == self.request.user

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        task = self.get_object()
        module = get_object_or_404(Module, pk=self.kwargs["module_pk"])
        course = module.course
        students_with_answers = task.answers.values_list("student", flat=True)
        students_without_answers = course.students.exclude(id__in=students_with_answers)
        context["students_without_answers"] = students_without_answers
        context.update({"module": module, "course": course})
        return context


class StudentQuizResultsListView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    """Результаты теста пользователей подписанных на курс"""
    template_name = "courses/manage/quiz/student_quiz_results.html"
    context_object_name = "results"

    def dispatch(self, request, *args, **kwargs):
        self.module = get_object_or_404(Module, pk=self.kwargs["module_pk"])
        self.course = self.module.course
        self.quiz = get_object_or_404(Quiz, pk=self.kwargs["quiz_pk"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.request.user == self.course.owner

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"course": self.course, "module": self.module, "quiz": self.quiz})
        return context

    def get_queryset(self):
        users = self.course.students.all()
        results = []
        users_without_results = []

        for user in users:
            user_results = StudentQuizResult.objects.filter(quiz=self.quiz, user=user)
            if user_results.exists():
                number_of_test_passes = user_results.count()
                first_score = user_results.first().score
                last_score = user_results.last().score
                date_of_last_test = user_results.last().created
                avg_score = user_results.aggregate(avg=Avg("score"))["avg"]

                results.append({
                    "user": user,
                    "number_of_test_passes": number_of_test_passes,
                    "first_score": first_score,
                    "last_score": last_score,
                    "date_of_last_test": date_of_last_test,
                    "avg_score": avg_score,
                })
            else:
                users_without_results.append({"user": user})

        results.extend(users_without_results)
        return results


class StudentAnswerCheckUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Проверка ответа пользователя на задание с выставлением балла"""
    model = StudentAnswer
    pk_url_kwarg = "answer_pk"
    fields = ["score", "comment"]
    template_name = "courses/manage/task/answer_check_update.html"

    def dispatch(self, request, *args, **kwargs):
        self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        self.module = Content.objects.get(
            content_type__model="task", object_id=self.kwargs["task_pk"]
        ).module
        self.course = self.module.course
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        return self.request.user == self.module.course.owner

    def form_valid(self, form):
        self.object.check_date = timezone.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["task"] = self.task
        context["answer"] = self.get_object()
        context.update({"course": self.course, "module": self.module})
        return context

    def get_success_url(self):
        return reverse(
            "module_task_detail",
            kwargs={"module_pk": self.module.pk, "task_pk": self.kwargs["task_pk"]},
        )
