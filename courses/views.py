from django.shortcuts import redirect, get_object_or_404
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.views.generic.base import TemplateResponseMixin, View
from django.views.generic.detail import DetailView
from django.urls import reverse_lazy, reverse
from .forms import ModuleFormSet
from .models import Course, Module, Content, Subject, Task, Quiz, Question, Answer
from accounts.models import StudentAnswer, StudentQuizResult
from django.contrib.auth.mixins import (
    LoginRequiredMixin,
    PermissionRequiredMixin,
    UserPassesTestMixin,
)
from django.apps import apps
from django.forms.models import modelform_factory, inlineformset_factory
from braces.views import CsrfExemptMixin, JsonRequestResponseMixin
from django.db.models import Count
from accounts.forms import CourseEnrollForm
from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponse
import os
from uuid import uuid4
from .widgets import DateTimePickerInput
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db.models import Avg


class OwnerMixin:
    def get_queryset(self):
        qs = super().get_queryset()
        return qs.filter(owner=self.request.user)


class OwnerEditMixin:
    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)


class OwnerCourseMixin(OwnerMixin, LoginRequiredMixin, PermissionRequiredMixin):
    model = Course
    fields = ["subject", "title", "overview"]
    success_url = reverse_lazy("manage_course_list")


class OwnerCourseEditMixin(OwnerCourseMixin, OwnerEditMixin):
    template_name = "courses/manage/course/form.html"


class ManageCourseListView(OwnerCourseMixin, ListView):
    template_name = "courses/manage/course/list.html"
    permission_required = "courses.view_course"


class CourseCreateView(OwnerCourseEditMixin, CreateView):
    permission_required = "courses.add_course"


class CourseUpdateView(OwnerCourseEditMixin, UpdateView):
    permission_required = "courses.change_course"


class CourseDeleteView(OwnerCourseMixin, DeleteView):
    template_name = "courses/manage/course/delete.html"
    permission_required = "courses.delete_course"


class CourseModuleUpdateView(TemplateResponseMixin, View):
    template_name = "courses/manage/module/formset.html"
    course = None

    def get_formset(self, data=None):
        return ModuleFormSet(instance=self.course, data=data)

    def dispatch(self, request, pk):
        self.course = get_object_or_404(Course, id=pk, owner=request.user)
        return super().dispatch(request, pk)

    def get(self, request, *args, **kwargs):
        formset = self.get_formset()
        return self.render_to_response({"course": self.course, "formset": formset})

    def post(self, request, *args, **kwargs):
        formset = self.get_formset(data=request.POST)
        if formset.is_valid():
            formset.save()
            # if module redirect to module_content_list else manage_course_list
            first_module = self.course.modules.first()
            if first_module:
                return redirect(
                    reverse_lazy(
                        "module_content_list", kwargs={"module_id": first_module.id}
                    )
                )
            else:
                return redirect("manage_course_list")
        return self.render_to_response({"course": self.course, "formset": formset})


class CourseStudentsDetailView(OwnerCourseMixin, DetailView):
    context_object_name = "course"
    permission_required = "courses.view_course"
    template_name = "courses/manage/course/list_of_course_students.html"


def exclude_student_from_course(request, course_pk, student_pk):
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        course = get_object_or_404(Course, pk=course_pk)
        student = get_object_or_404(get_user_model(), pk=student_pk)
        course.students.remove(student)
        return JsonResponse(
            {
                "status": f"student '{student.get_full_name}' removed from '{course.title}' successfully"
            }
        )


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
    """Версия QuestionAnswerCreateUpdate для"""

    template_name = "courses/manage/quiz/quiz_manage_questions.html"

    def get_question_form(self, data=None):
        QuestionForm = modelform_factory(
            Question,
            fields=["text"],
        )
        return QuestionForm(instance=self.question_instance, data=data)

    def get_answer_inlineformset(self, data=None):
        num_of_answers = (
            self.quiz.number_of_answers
        )  # Количество доп. полей для ответов
        if self.question_instance:
            num_of_answers -= (
                self.question_instance.answers.count()
            )  # Доп. поля с учетом существующих
        AnswerFormSet = inlineformset_factory(
            Question,
            Answer,
            fields=["text", "correct"],
            extra=num_of_answers,  # self.quiz.number_of_answers
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
        # Получить Content->Module->Course, указав модель контента и pk объекта
        if self.course.owner == self.request.user:
            return True

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
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        content = get_object_or_404(
            Content, pk=content_pk, module__course__owner=request.user
        )
        content.item.delete()
        content.delete()
        return JsonResponse({"status": f"Content deleted successfully"})


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


class CourseListView(TemplateResponseMixin, View):
    model = Course
    template_name = "courses/course/list.html"

    def get(self, reguest, subject=None, teacher_pk=None):
        subjects = cache.get("all_subjects")
        if not subjects:
            subjects = Subject.objects.annotate(total_courses=Count("courses"))
            # cache.set("all_subjects", subjects)
        all_courses = Course.objects.annotate(
            total_modules=Count("modules")
        ).select_related("owner", "subject")

        if subject:
            subject = get_object_or_404(Subject, slug=subject)
            key = f"subject_{subject.id}_courses"
            courses = cache.get(key)
            if not courses:
                courses = all_courses.filter(subject=subject)
                # cache.set(key, courses)
        elif teacher_pk:
            courses = all_courses.filter(owner=teacher_pk)
        else:
            courses = cache.get("all_courses")
            if not courses:
                courses = all_courses
                # cache.set("all_courses", courses)

        return self.render_to_response(
            {
                "subjects": subjects,
                "subject": subject,
                "courses": courses.order_by("-created"),
            }
        )


class TaskDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """Задание и список ответов"""

    model = Task
    pk_url_kwarg = "task_pk"
    context_object_name = "task"
    template_name = "courses/manage/task/task_detail.html"

    def test_func(self):
        obj = self.get_object()
        if obj.owner == self.request.user:
            return True
        return False

    def get_context_data(self, **kwargs):
        """Определяем студентов, которые сдали задание и не сдали"""
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
        """Извлекаем необходимые экземпляры"""
        self.module = get_object_or_404(Module, pk=self.kwargs["module_pk"])
        self.course = self.module.course
        self.quiz = get_object_or_404(Quiz, pk=self.kwargs["quiz_pk"])
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        if self.request.user == self.course.owner:
            return True

    def get_context_data(self, **kwargs):
        """Добавляем необходимые экземпляры в Context"""
        context = super().get_context_data(**kwargs)
        context.update(
            {"course": self.course, "module": self.module, "quiz": self.quiz}
        )
        return context

    def get_queryset(self):
        # Список пользователей подписанных на курс
        users = self.course.students.all()
        results = []
        users_without_results = []

        # Для каждого пользователя получаем результат
        for user in users:
            user_results = StudentQuizResult.objects.filter(quiz=self.quiz, user=user)

            # Если у пользователя есть результаты
            if user_results.exists():
                number_of_test_passes = user_results.count()
                first_score = user_results.first().score
                last_score = user_results.last().score
                date_of_last_test = user_results.last().created
                avg_score = user_results.aggregate(avg=Avg("score"))["avg"]

                # Добавляем результаты в список
                results.append(
                    {
                        "user": user,
                        "number_of_test_passes": number_of_test_passes,
                        "first_score": first_score,
                        "last_score": last_score,
                        "date_of_last_test": date_of_last_test,
                        "avg_score": avg_score,
                    }
                )
            # Если пользователь не проходил тест
            else:
                users_without_results.append({"user": user})

        # Добовляем в конец списка пользоваетелей без результатов
        results.extend(users_without_results)

        # Возвращаем результаты
        return results


class StudentAnswerCheckUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """Проверка ответа пользователя на задание с выставлением балла (score)"""

    model = StudentAnswer
    pk_url_kwarg = "answer_pk"
    fields = ["score", "comment"]
    template_name = "courses/manage/task/answer_check_update.html"

    def dispatch(self, request, *args, **kwargs):
        self.task = self.task = get_object_or_404(Task, pk=self.kwargs["task_pk"])
        self.module = Content.objects.get(
            content_type__model="task", object_id=self.kwargs["task_pk"]
        ).module
        self.course = self.module.course
        return super().dispatch(request, *args, **kwargs)

    def test_func(self):
        """Доступ только автору курса"""
        if self.request.user == self.module.course.owner:
            return True

    def form_valid(self, form):
        self.object.check_date = timezone.now()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        obj = self.get_object()
        context["task"] = self.task
        context["answer"] = obj
        context.update({"course": self.course, "module": self.module})
        return context

    def get_success_url(self):
        return reverse(
            "module_task_detail",
            kwargs={"module_pk": self.module.pk, "task_pk": self.kwargs["task_pk"]},
        )


class CourseDetailView(DetailView):
    model = Course
    template_name = "courses/course/detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["enroll_form"] = CourseEnrollForm(initial={"course": self.object})
        return context


@csrf_exempt  # Исключить csrf. Необходима защита?
def upload_image(request, module_id=None, model_name=None, id=None):
    """
    Функция обработки загрузки изображения TinyMCE
    """
    if request.method != "POST":
        return JsonResponse({"Error Message": "Wrong request"})

    # Проверяем модуль и пользователя
    matching_module = get_object_or_404(
        Module, id=module_id, course__owner=request.user
    )

    # Получаем file
    file_obj = request.FILES["file"]
    # Извлекаем формат изображения и проверяем его
    file_name_suffix = file_obj.name.split(".")[-1]
    if file_name_suffix not in ["jpg", "png", "gif", "jpeg"]:
        return JsonResponse(
            {
                "Error Message": f"Wrong file suffix ({file_name_suffix}), supported qre .jpg, .png, .gif, jpeg"
            }
        )

    # Строим путь по типу "root/course-slug_id_*/module_id_*/"
    path = os.path.join(
        settings.MEDIA_ROOT,
        matching_module.course.slug + f"_id_{matching_module.course.id}",
        f"module_id_{matching_module.id}",
    )
    # Если path не существует то строим
    if os.path.exists(path) == False:
        os.makedirs(path)

    # Строим путь + имя файла
    file_path = os.path.join(
        path,
        file_obj.name,
    )

    if os.path.exists(file_path):
        file_obj.name = str(uuid4()) + "." + file_name_suffix
        file_path = os.path.join(path, file_obj.name)

    # Записываем файл по пути file_path
    with open(file_path, "wb+") as f:
        for chunk in file_obj.chunks():
            f.write(chunk)

        # Возвращаем требуемый путь к файлу для tinyMCE, но с MEDIA_URL
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
