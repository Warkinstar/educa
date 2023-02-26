from django.shortcuts import render
from courses.models import Quiz
from django.views.generic import ListView
from django.http import JsonResponse
from courses.models import Question, Answer
from accounts.models import StudentQuizResult


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
            question = Question.objects.get(text=k)  # извлекаем экземпляры вопросов
            questions.append(question)
        print(questions)

        user = request.user
        quiz = Quiz.objects.get(pk=pk)

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
