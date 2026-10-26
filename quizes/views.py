from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.contenttypes.models import ContentType
from courses.models import Content, Quiz
from courses.progress_service import can_open_module
from django.views.generic import ListView, CreateView, UpdateView
from django.views.generic.base import TemplateResponseMixin
from django.views import View
from django.http import Http404, JsonResponse
from courses.models import Question, Answer
from accounts.models import StudentQuizResult
from django.urls import reverse_lazy, reverse
from django.forms import inlineformset_factory, modelform_factory
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.contrib.auth.decorators import login_required, permission_required


def _get_quiz_or_404(pk):
    try:
        quiz_id = int(pk)
    except (TypeError, ValueError) as exc:
        raise Http404("Тест не найден") from exc
    return get_object_or_404(Quiz, pk=quiz_id)


def _check_quiz_access(quiz, user):
    """
    Проверяет привязку теста к курсу/модулю и доступность модуля для пользователя.
    Возвращает кортеж `(is_allowed, reason, course, module, has_course_access)`.
    """
    quiz_ct = ContentType.objects.get_for_model(Quiz)
    content = (
        Content.objects.filter(content_type=quiz_ct, object_id=quiz.pk)
        .select_related("module__course")
        .first()
    )
    if content is None:
        return True, None, None, None, True

    module = content.module
    course = module.course

    has_course_access, course_reason = course.can_user_access(user)
    if not has_course_access:
        return (
            False,
            course_reason or "У вас нет доступа к этому курсу.",
            course,
            module,
            False,
        )

    is_open, lock_reason = can_open_module(module, user)
    if not is_open:
        return (
            False,
            lock_reason or "Модуль закрыт для прохождения.",
            course,
            module,
            True,
        )

    return True, None, course, module, True


class QuizListView(ListView):
    """Список тестов"""

    model = Quiz
    template_name = "quizes/main.html"


class QuizDetailView(LoginRequiredMixin, View):
    """Страница теста"""

    def get(self, request, pk, *args, **kwargs):
        quiz = _get_quiz_or_404(pk)
        is_allowed, reason, course, module, has_course_access = _check_quiz_access(
            quiz, request.user
        )
        if not is_allowed:
            return render(
                request,
                "quizes/quiz_forbidden.html",
                {
                    "obj": quiz,
                    "reason": reason,
                    "course": course,
                    "module": module,
                    "has_course_access": has_course_access,
                },
                status=403,
            )
        return render(
            request,
            "quizes/quiz.html",
            {
                "obj": quiz,
                "course": course,
                "module": module,
            },
        )


class QuizDataView(LoginRequiredMixin, View):
    """Обрабатывает ajax запрос, возвращает Вопросы с соответствующими Ответами и время"""

    def get(self, request, pk, *args, **kwargs):
        quiz = _get_quiz_or_404(pk)
        is_allowed, reason, _, _, _ = _check_quiz_access(quiz, request.user)
        if not is_allowed:
            return JsonResponse({"error": reason}, status=403)

        questions = []
        for q in quiz.get_questions():
            answers = []
            for a in q.get_answers():
                answers.append(a.text)
            questions.append({str(q): answers})
        return JsonResponse(
            {
                "data": questions,
                "time": quiz.time,
            }
        )


class QuizSaveView(LoginRequiredMixin, View):
    """Обрабатывает сохранение результатов прохождения теста"""

    def post(self, request, pk, *args, **kwargs):
        user = request.user
        quiz = _get_quiz_or_404(pk)
        is_allowed, reason, _, _, _ = _check_quiz_access(quiz, user)
        if not is_allowed:
            return JsonResponse({"error": reason}, status=403)

        # Проверка что запрос типа ajax
        # request.is_ajax() для синхронного, а для асинхронного веб сервера:
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            questions = []
            data = request.POST
            # Преобразуем данные QueryDict в словарь {"1+ 1 = ?": ["2"]}
            data_ = dict(data.lists())
            data_.pop("csrfmiddlewaretoken", None)  # Убираем из словаря csrf

            for k in data_.keys():
                # Обход исключения, если вопрос повторяется Было: .get(text=k)
                question = Question.objects.filter(
                    quiz=quiz, text=k
                ).first()  # извлекаем экземпляры вопросов
                questions.append(question)

            score = 0  # Счет
            multiplier = 100 / quiz.number_of_questions  # множитель
            results = []
            correct_answer = None

            for q in questions:
                # извлекаем из POST, ответ который выбрал пользователь
                a_selected = request.POST.get(str(q))

                # Если пользователь хоть что-то отметил
                if a_selected != "":
                    # Извлекаем все ответы на выбранный вопрос
                    question_answers = Answer.objects.filter(question=q)
                    for a in question_answers:  # Перебираем ответы на выбранный вопрос
                        if a_selected == a.text:  # Если выбранный ответ совпадает
                            if a.correct:  # Если ответ из списка правильный
                                score += 1
                                correct_answer = a.text
                        else:  # Если ответ не совпадает
                            if a.correct:  # И ответ из списка перебираемых правельный
                                correct_answer = a.text  # score не увеличиваем

                    results.append(
                        {str(q): {"correct_answer": correct_answer, "answered": a_selected}}
                    )
                else:  # Если пользователь ничего не отметил
                    results.append({str(q): "не отмечен"})

            # Формируем счет
            score_ = score * multiplier
            StudentQuizResult.objects.create(quiz=quiz, user=user, score=score_)

            # Смотрим набрал ли пользователь проходной балл
            if score_ >= quiz.required_score_to_pass:
                return JsonResponse({"passed": True, "score": score_, "results": results})
            else:
                return JsonResponse({"passed": False, "score": score_, "results": results})

        return JsonResponse({"error": "Некорректный запрос."}, status=400)


class QuizCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    permission_required = "courses.add_quiz"
    model = Quiz
    template_name = "quizes/quiz_form.html"
    fields = [
        "topic",
        "title",
        "number_of_questions",
        "number_of_answers",
        "required_score_to_pass",
    ]

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("quizes:quiz-view", kwargs={"pk": self.object.pk})


class QuizUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    permission_required = "courses.change_quiz"
    model = Quiz
    template_name = "quizes/quiz_form.html"
    fields = [
        "topic",
        "title",
        "number_of_questions",
        "number_of_answers",
        "required_score_to_pass",
    ]

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_success_url(self):
        return reverse("quizes:quiz-view", kwargs={"pk": self.object.pk})


class QuestionAnswerCreateUpdateView(LoginRequiredMixin, PermissionRequiredMixin, TemplateResponseMixin, View):
    permission_required = "courses.change_quiz"
    template_name = "quizes/quiz_manage_questions.html"

    def get_question_form(self, data=None):
        QuestionForm = modelform_factory(
            Question,
            fields=["text"],
        )
        return QuestionForm(instance=self.question_instance, data=data)

    def get_answer_inlineformset(self, data=None):
        AnswerFormSet = inlineformset_factory(
            Question,
            Answer,
            fields=["text", "correct"],
            max_num=self.quiz.number_of_answers,  # self.quiz.number_of_answers
            can_delete=False,
        )
        return AnswerFormSet(instance=self.question_instance, data=data)

    def dispatch(self, request, quiz_pk, question_pk=None):
        self.quiz = get_object_or_404(Quiz, id=quiz_pk, owner=request.user)
        if question_pk:
            self.question_instance = get_object_or_404(
                Question, pk=question_pk, quiz=self.quiz
            )
        else:
            self.question_instance = None
        return super().dispatch(request, quiz_pk)

    def get(self, request, *args, **kwargs):
        question_form = self.get_question_form()
        answer_formset = self.get_answer_inlineformset()
        return self.render_to_response(
            {
                "quiz": self.quiz,
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
                return redirect("quizes:quiz_manage", quiz_pk=self.quiz.pk)
            return redirect("quizes:quiz-view", pk=self.quiz.pk)

        return self.render_to_response(
            {
                "quiz": self.quiz,
                "question_form": question_form,
                "answer_formset": answer_formset,
            }
        )

@login_required
@permission_required("courses.delete_question", raise_exception=True)
def question_delete(request, question_pk):
    """Функция удаления вопроса, ожидающая ajax запрос"""
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        question = get_object_or_404(Question, pk=question_pk, quiz__owner=request.user)
        question.delete()
        return JsonResponse({"status": "success"})
    return JsonResponse({"status": "error"}, status=400)
