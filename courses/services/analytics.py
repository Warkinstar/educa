from django.db.models import Avg, Max, Count
from courses.models import CourseProgress, Quiz
from accounts.models import StudentQuizResult
from courses.progress_service import calculate_progress


def get_course_analytics_data(course):
    """
    Формирует аналитику по курсу для преподавателя:
    общие показатели группы и построчная статистика по каждому студенту.
    """
    students = course.students.all().order_by('last_name', 'first_name', 'username')
    modules = list(course.modules.all())
    total_modules_count = len(modules)

    # Все тесты курса через его модули
    students = course.students.all().order_by('last_name', 'first_name', 'username')
    modules = list(course.modules.all())
    total_modules_count = len(modules)

    # Тесты курса через полиморфную связь Content
    quizzes = list(Quiz.objects.filter(contents__module__in=modules).distinct())
    total_quizzes_count = len(quizzes)

    # Словарь сохранённого прогресса студентов по курсу
    progress_records = {
        cp.user_id: cp
        for cp in CourseProgress.objects.filter(course=course, user__in=students)
    }

    students_summary = []
    total_progress_sum = 0
    completed_students_count = 0
    all_scores = []

    for student in students:
        # 1. Прогресс прохождения курса через calculate_progress
        student_course_progress = progress_records.get(student.id)

        if student_course_progress:
            completed_modules_count = student_course_progress.completed_modules.count()
            progress_percent = calculate_progress(completed_modules_count, total_modules_count)
            is_completed = (progress_percent == 100) or getattr(student_course_progress, 'is_completed', False)
            completed_at = student_course_progress.completed_at
            last_activity = getattr(student_course_progress, 'last_activity_at', None) or getattr(student_course_progress, 'updated_at', None)
        else:
            progress_percent = 0
            is_completed = False
            completed_at = None
            last_activity = None

        total_progress_sum += progress_percent
        if is_completed:
            completed_students_count += 1

        # 2. Результаты тестов (поля score и created)
        quiz_results = StudentQuizResult.objects.filter(
            user=student,
            quiz__in=quizzes
        )

        test_stats = quiz_results.aggregate(
            avg_score=Avg('score'),
            total_attempts=Count('id'),
            last_test_date=Max('created')
        )

        avg_score = round(test_stats['avg_score'], 1) if test_stats['avg_score'] is not None else None
        if avg_score is not None:
            all_scores.append(avg_score)

        # Подсчёт сданных тестов (лучший балл >= проходного)
        passed_quizzes_count = 0
        for quiz in quizzes:
            best_score = quiz_results.filter(quiz=quiz).aggregate(max_score=Max('score'))['max_score']
            if best_score is not None and best_score >= quiz.required_score_to_pass:
                passed_quizzes_count += 1

        # Определение времени последней активности
        latest_activity = last_activity
        if test_stats['last_test_date']:
            if not latest_activity or test_stats['last_test_date'] > latest_activity:
                latest_activity = test_stats['last_test_date']

        students_summary.append({
            'user': student,
            'full_name': student.get_full_name() or student.username,
            'username': student.username,
            'email': student.email or '—',
            'progress_percent': progress_percent,
            'is_completed': is_completed,
            'completed_at': completed_at,
            'passed_quizzes_count': passed_quizzes_count,
            'total_quizzes_count': total_quizzes_count,
            'avg_score': avg_score,
            'total_attempts': test_stats['total_attempts'] or 0,
            'last_activity': latest_activity,
        })
        
    total_students_count = len(students)
    group_avg_progress = round(total_progress_sum / total_students_count, 1) if total_students_count > 0 else 0
    group_avg_score = round(sum(all_scores) / len(all_scores), 1) if all_scores else None

    return {
        'course': course,
        'total_students_count': total_students_count,
        'group_avg_progress': group_avg_progress,
        'group_avg_score': group_avg_score,
        'completed_students_count': completed_students_count,
        'total_modules_count': total_modules_count,
        'total_quizzes_count': total_quizzes_count,
        'students_summary': students_summary,
    }