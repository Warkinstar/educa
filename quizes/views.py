from django.shortcuts import render, get_object_or_404, redirect
from courses.models import Quiz
from django.views.generic import ListView, CreateView
from django.views.generic.base import TemplateResponseMixin
from django.views import View
from django.http import JsonResponse
from courses.models import Question, Answer
from accounts.models import StudentQuizResult
from django.urls import reverse_lazy, reverse
from django.forms import inlineformset_factory, modelform_factory


class QuizListView(ListView):
    """Список тестов"""

    model = Quiz
    template_name = "quizes/main.html"


def quiz_view(request, pk):
    """Страница теста"""

    quiz = Quiz.objects.get(pk=pk)
    return render(request, "quizes/quiz.html", {"obj": quiz})


def quiz_data_view(request, pk):
    """Обрабатывает ajax запрос, возвращает Вопросы с соответствующими Ответами и время"""

    quiz = Quiz.objects.get(pk=pk)
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


def save_quiz_view(request, pk):
    user = request.user
    quiz = Quiz.objects.get(pk=pk)

    # print(request.POST)
    # Проверка что запрос типа ajax
    # request.is_ajax() для синхронного, а для ассинхронного веб сервера:
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        questions = []
        data = request.POST
        # Преобразуем данные QueryDict в словарь {"1+ 1 = ?": ["2"},
        data_ = dict(data.lists())
        data_.pop("csrfmiddlewaretoken")  # Убираем из словаря csrf

        for k in data_.keys():
            print("key: ", k)  # Извлекаем вопросы
            # Обход исключения, если вопрос повторяется Было: .get(text=k)
            question = Question.objects.filter(
                quiz=quiz, text=k
            ).first()  # извлекаем экземпляры вопросов
            questions.append(question)
        print(questions)

        score = 0  # Счет
        multiplier = 100 / quiz.number_of_questions  # множитель
        results = []
        correct_answer = None

        for q in questions:
            # извлекаем из POST, ответ который выбрал пользователь
            a_selected = request.POST.get(str(q))
            print("selected", a_selected)

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


class QuizCreateView(CreateView):
    model = Quiz
    template_name = "quizes/quiz_new.html"
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


class QuestionAnswerCreateUpdateView(TemplateResponseMixin, View):
    template_name = "quizes/quiz_manage_questions.html"

    def get_question_form(self, data=None):
        QuestionForm = modelform_factory(
            Question,
            fields=["text"],
        )
        return QuestionForm(data=data)

    def get_answer_inlineformset(self, data=None):
        AnswerFormSet = inlineformset_factory(
            Question,
            Answer,
            fields=["text", "correct"],
            max_num=self.quiz.number_of_answers,  # self.quiz.number_of_answers
            can_delete=False,
        )
        return AnswerFormSet(instance=None, data=data)

    def dispatch(self, request, quiz_pk):
        self.quiz = get_object_or_404(Quiz, id=quiz_pk)
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


def question_delete(request, question_pk):
    """Функция удаления вопроса, ожидающая ajax запрос"""
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        question = get_object_or_404(Question, pk=question_pk)
        question.delete()
        return JsonResponse({"status": "success"})
