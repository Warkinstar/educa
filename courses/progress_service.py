"""
Сервисный слой расчёта прогресса и правил доступа к модулям курса.

Правила открытия модуля (в строгом порядке приоритета):
1. Доступ к курсу (`course.can_user_access(user)`).
2. Прохождение всех предыдущих стоп-модулей (`Module.is_stop=True`).
3. Наступление даты открытия по ритму (`get_course_start + timedelta(days=module.open_after_days)`).

Автор курса (`course.owner == user`) видит и открывает все модули без ограничений
и без записи прогресса прохождения.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Max, Prefetch, Q
from django.utils import timezone

from accounts.models import StudentQuizResult

from .models import (
    Content,
    CourseAssignment,
    CourseProgress,
    Module,
    ModuleProgress,
    Quiz,
)


def _resolve_course_start(course, user, now=None):
    """
    Внутренняя функция расчёта точки отсчёта старта курса с переданным временем `now`.
    """
    current_time = now
    if current_time is None:
        current_time = timezone.now()

    if not user or not user.is_authenticated:
        return current_time

    assignment = course.get_current_assignment_for_user(user)
    if assignment is not None:
        if assignment.activated_at is not None:
            return assignment.activated_at
        return assignment.assigned_at

    progress = (
        CourseProgress.objects.filter(course=course, user=user)
        .only("started_at")
        .first()
    )
    if progress is not None:
        return progress.started_at

    return current_time


def get_course_start(course, user):
    """
    Возвращает дату и время старта курса для пользователя.

    - Если есть действующее назначение (`course.get_current_assignment_for_user(user)`):
      возвращает `activated_at`, а если оно не задано — `assigned_at`.
    - При самозаписи возвращает `started_at` из `CourseProgress`
      (если запись ещё не создана — текущее время `timezone.now()`).
    """
    return _resolve_course_start(course, user)


def ensure_course_started(course, user):
    """
    Создаёт запись `CourseProgress` при первом открытии курса студентом
    (если пользователь авторизован и не является автором курса).
    Для автора курса прогресс не создаётся.
    """
    if not user or not user.is_authenticated:
        return None
    if course.owner_id == user.pk:
        return None

    progress, _ = CourseProgress.objects.get_or_create(
        user=user,
        course=course,
        defaults={"started_at": timezone.now()},
    )
    return progress


def _load_course_modules_with_items(course):
    """
    Загружает все модули курса в порядке `(order, id)` вместе с элементами `Content`
    и связанными полиморфными объектами (`GenericForeignKey`) за фиксированное число запросов.
    """
    contents_qs = (
        Content.objects.select_related("content_type")
        .prefetch_related("item")
        .order_by("order", "id")
    )
    return list(
        Module.objects.filter(course=course)
        .prefetch_related(Prefetch("contents", queryset=contents_qs))
        .order_by("order", "id")
    )


def _preload_quiz_progress_for_modules(modules, user):
    """
    Собирает квизы модулей из уже предзагруженного `contents` и одним запросом
    загружает лучшие результаты пользователя (`StudentQuizResult`) по всем квизам курса.
    Сохраняет предзагруженные данные на объектах модулей (`prefetched_quizzes`, `all_quizzes_passed`).
    """
    quizzes_by_module = {}
    all_quiz_ids = set()

    for module in modules:
        module_quizzes = []
        for content in module.contents.all():
            if isinstance(content.item, Quiz):
                module_quizzes.append(content.item)
                all_quiz_ids.add(content.item.id)
        quizzes_by_module[module.id] = module_quizzes

    max_scores_by_quiz = {}
    if all_quiz_ids and user and user.is_authenticated:
        score_rows = (
            StudentQuizResult.objects.filter(user=user, quiz_id__in=all_quiz_ids)
            .values("quiz_id")
            .annotate(max_score=Max("score"))
        )
        max_scores_by_quiz = {
            row["quiz_id"]: row["max_score"] for row in score_rows
        }

    for module in modules:
        module_quizzes = quizzes_by_module[module.id]
        unpassed_quizzes = []
        for quiz in module_quizzes:
            best_score = max_scores_by_quiz.get(quiz.id)
            if best_score is None or best_score < quiz.required_score_to_pass:
                unpassed_quizzes.append(quiz)
        module.prefetched_quizzes = module_quizzes
        module.unpassed_quizzes = unpassed_quizzes
        module.all_quizzes_passed = len(unpassed_quizzes) == 0


def _evaluate_single_module_lock(
    module,
    has_course_access,
    course_lock_reason,
    blocking_stop_module,
    course_start,
    now,
):
    """
    Проверяет доступность одного модуля в строгом порядке:
    1) доступ к курсу -> 2) предыдущие стоп-модули -> 3) ритм открытия (`open_after_days`).
    Возвращает кортеж `(is_open: bool, lock_reason: str | None)`.
    """
    if not has_course_access:
        return False, course_lock_reason

    if blocking_stop_module is not None:
        return False, f"Сначала пройдите модуль «{blocking_stop_module.title}»"

    if module.open_after_days:
        open_at = course_start + timedelta(days=module.open_after_days)
        if now < open_at:
            local_open_at = timezone.localtime(open_at)
            return False, f"Откроется {local_open_at.strftime('%d.%m.%Y')}"

    return True, None


def get_modules_state(course, user):
    """
    Возвращает упорядоченный по `(order, id)` список состояний всех модулей курса:
    `{"module": module, "is_completed": bool, "is_open": bool, "lock_reason": str | None}`.

    Число SQL-запросов константно и не зависит от количества модулей в курсе.
    """
    modules = _load_course_modules_with_items(course)
    if not modules:
        return []

    is_authenticated = bool(user and user.is_authenticated)
    if is_authenticated and course.owner_id == user.pk:
        _preload_quiz_progress_for_modules(modules, user)
        return [
            {
                "module": module,
                "is_completed": False,
                "is_open": True,
                "lock_reason": None,
            }
            for module in modules
        ]

    _preload_quiz_progress_for_modules(modules, user)

    completed_module_ids = set()
    if is_authenticated:
        module_ids = [m.id for m in modules]
        completed_module_ids = set(
            ModuleProgress.objects.filter(
                user=user,
                module_id__in=module_ids,
            ).values_list("module_id", flat=True)
        )

    now = timezone.now()
    has_course_access, course_lock_reason = course.can_user_access(user)

    course_start = now
    if has_course_access:
        course_start = _resolve_course_start(course, user, now=now)

    states = []
    blocking_stop_module = None

    for module in modules:
        is_completed = module.id in completed_module_ids
        is_open, lock_reason = _evaluate_single_module_lock(
            module=module,
            has_course_access=has_course_access,
            course_lock_reason=course_lock_reason,
            blocking_stop_module=blocking_stop_module,
            course_start=course_start,
            now=now,
        )

        states.append(
            {
                "module": module,
                "is_completed": is_completed,
                "is_open": is_open,
                "lock_reason": lock_reason,
            }
        )

        if module.is_stop and not is_completed and blocking_stop_module is None:
            blocking_stop_module = module

    return states


def can_open_module(module, user):
    """
    Проверяет, может ли пользователь открыть указанный модуль.
    Возвращает кортеж `(is_open: bool, reason: str | None)`.

    Использует единый расчёт `get_modules_state` без дублирования правил блокировки.
    """
    states = get_modules_state(module.course, user)
    for state in states:
        if state["module"].pk == module.pk:
            return state["is_open"], state["lock_reason"]

    return False, "Модуль не найден в курсе"


def _fetch_unpassed_module_quizzes(module, user):
    """
    Запрашивает из БД список несданных тестов (`Quiz`) указанного модуля
    в порядке следования контента модуля (`order, id`).
    """
    if not user or not user.is_authenticated:
        return []

    quiz_ct = ContentType.objects.get_for_model(Quiz)
    quiz_ids = list(
        Content.objects.filter(
            module=module,
            content_type=quiz_ct,
        )
        .order_by("order", "id")
        .values_list("object_id", flat=True)
    )
    if not quiz_ids:
        return []

    quizzes_by_id = Quiz.objects.in_bulk(quiz_ids)
    ordered_quizzes = [
        quizzes_by_id[qid] for qid in quiz_ids if qid in quizzes_by_id
    ]
    if not ordered_quizzes:
        return []

    score_rows = (
        StudentQuizResult.objects.filter(user=user, quiz_id__in=quiz_ids)
        .values("quiz_id")
        .annotate(max_score=Max("score"))
    )
    max_scores_by_quiz = {
        row["quiz_id"]: row["max_score"] for row in score_rows
    }

    unpassed = []
    for quiz in ordered_quizzes:
        best_score = max_scores_by_quiz.get(quiz.id)
        if best_score is None or best_score < quiz.required_score_to_pass:
            unpassed.append(quiz)
    return unpassed


def get_module_unpassed_quizzes(module, user):
    """
    Возвращает список несданных тестов (`Quiz`) модуля для пользователя.
    Если модуль был получен через `get_modules_state`, использует уже
    предзагруженный список `module.unpassed_quizzes` без лишних SQL-запросов.
    Для автора курса возвращает пустой список.
    """
    if module is None or not user or not user.is_authenticated:
        return []
    if module.course.owner_id == user.pk:
        return []
    if hasattr(module, "unpassed_quizzes"):
        return list(module.unpassed_quizzes)
    return _fetch_unpassed_module_quizzes(module, user)


def _validate_module_quizzes_passed(module, user):
    """
    Проверяет, что все тесты (`Quiz`) внутри модуля сданы пользователем
    на проходной балл (`score >= required_score_to_pass`).
    Задания (`Task`) завершение модуля не блокируют.
    """
    unpassed_quizzes = _fetch_unpassed_module_quizzes(module, user)
    if unpassed_quizzes:
        quiz = unpassed_quizzes[0]
        raise ValidationError(
            f"Не все тесты модуля успешно сданы: пройдите тест «{quiz.title}» "
            f"(минимум {quiz.required_score_to_pass}%)."
        )


def complete_module(module, user):
    """
    Отмечает модуль как пройденный пользователем.

    - Проверяет доступность модуля через `can_open_module(module, user)`.
    - Проверяет успешную сдачу всех тестов (`Quiz`) модуля (`Task` не блокируют).
    - Для автора курса прогресс не записывается.
    - Атомарно создаёт `ModuleProgress` (идемпотентно при повторном вызове)
      и при прохождении всех модулей курса фиксирует `CourseProgress.completed_at`.
    """
    is_open, lock_reason = can_open_module(module, user)
    if not is_open:
        raise ValidationError(lock_reason or "Модуль недоступен для прохождения.")

    course = module.course
    if course.owner_id == user.pk:
        return None

    _validate_module_quizzes_passed(module, user)

    with transaction.atomic():
        module_progress, _ = ModuleProgress.objects.get_or_create(
            user=user,
            module=module,
        )

        total_modules = course.modules.count()
        completed_modules = ModuleProgress.objects.filter(
            user=user,
            module__course=course,
        ).count()

        if total_modules > 0 and completed_modules >= total_modules:
            now = timezone.now()
            course_progress, _ = CourseProgress.objects.get_or_create(
                user=user,
                course=course,
                defaults={"started_at": _resolve_course_start(course, user, now=now)},
            )
            if course_progress.completed_at is None:
                course_progress.completed_at = now
                course_progress.save(update_fields=["completed_at"])

        return module_progress


def get_course_progress_percent(course, user):
    """
    Возвращает процент пройденных пользователем модулей курса (целое число от 0 до 100).
    Если в курсе нет модулей или пользователь не авторизован — возвращает 0.
    """
    if not user or not user.is_authenticated:
        return 0

    stats = course.modules.aggregate(
        total=Count("id", distinct=True),
        completed=Count(
            "id",
            filter=Q(user_progresses__user=user),
            distinct=True,
        ),
    )
    total = stats["total"] or 0
    if total == 0:
        return 0

    completed = stats["completed"] or 0
    percent = round(completed * 100 / total)
    return min(100, max(0, int(percent)))


def select_default_module_state(modules_state):
    """
    Выбирает активный модуль по умолчанию (когда `module_id` не передан в URL):
    1) первый открытый и НЕпройденный модуль;
    2) если все открытые модули уже пройдены — последний открытый модуль;
    3) если открытых модулей нет — `None`.
    """
    for state in modules_state:
        if state["is_open"] and not state["is_completed"]:
            return state

    open_states = [state for state in modules_state if state["is_open"]]
    if open_states:
        return open_states[-1]

    return None


def select_redirect_module_state(modules_state):
    """
    Выбирает модуль для редиректа при попытке прямого перехода к закрытому модулю:
    1) первый открытый и непройденный модуль;
    2) иначе — первый доступный (открытый) модуль;
    3) если открытых модулей нет — `None`.
    """
    for state in modules_state:
        if state["is_open"] and not state["is_completed"]:
            return state

    for state in modules_state:
        if state["is_open"]:
            return state

    return None


def select_next_open_module(course, user, current_module):
    """
    Определяет следующий открытый модуль курса после завершения `current_module`:
    1) первый открытый непройденный модуль после текущего;
    2) первый открытый непройденный модуль с начала курса (если был пропущен ранее);
    3) первый открытый модуль после текущего;
    4) текущий модуль, если он остаётся открытым;
    5) иначе — модуль по умолчанию (`select_default_module_state`).
    """
    states = get_modules_state(course, user)
    if not states:
        return None

    current_idx = None
    for idx, state in enumerate(states):
        if state["module"].pk == current_module.pk:
            current_idx = idx
            break

    if current_idx is not None:
        for state in states[current_idx + 1 :]:
            if state["is_open"] and not state["is_completed"]:
                return state["module"]

        for state in states[:current_idx]:
            if state["is_open"] and not state["is_completed"]:
                return state["module"]

        for state in states[current_idx + 1 :]:
            if state["is_open"]:
                return state["module"]

        if states[current_idx]["is_open"]:
            return states[current_idx]["module"]

    fallback_state = select_default_module_state(states)
    return fallback_state["module"] if fallback_state is not None else None


def get_course_students_progress(course):
    """
    Собирает уникальный список студентов курса (самозапись `course.students` +
    действующие `CourseAssignment` курса — как личные, так и через активные учебные группы)
    и возвращает сводку их прогресса за константное число SQL-запросов O(1) без N+1.
    """
    user_model = get_user_model()
    total_modules = Module.objects.filter(course=course).count()

    self_enrolled_ids = set(course.students.values_list("id", flat=True))
    active_assignments = list(
        CourseAssignment.objects.filter(
            course=course,
            is_active=True,
        )
        .filter(
            Q(group_assignment__isnull=True) | Q(group_assignment__is_active=True)
        )
        .select_related("group_assignment__group")
        .order_by("-assigned_at", "-id")
    )

    assignments_by_user_id = {}
    for assignment in active_assignments:
        if assignment.user_id not in assignments_by_user_id:
            assignments_by_user_id[assignment.user_id] = assignment

    student_ids = self_enrolled_ids | set(assignments_by_user_id.keys())
    if not student_ids:
        return {
            "total_modules": total_modules,
            "completed_students_count": 0,
            "students_progress": [],
        }

    users = list(
        user_model.objects.filter(id__in=student_ids).order_by(
            "last_name", "first_name", "username", "id"
        )
    )

    course_progress_by_user_id = {
        cp.user_id: cp
        for cp in CourseProgress.objects.filter(
            course=course,
            user_id__in=student_ids,
        )
    }

    completed_counts = {}
    last_module_by_user_id = {}
    last_module_completed_at_by_user_id = {}

    module_progresses = (
        ModuleProgress.objects.filter(
            module__course=course,
            user_id__in=student_ids,
        )
        .select_related("module")
        .order_by("-completed_at", "-module__order", "-id")
    )
    for mp in module_progresses:
        uid = mp.user_id
        completed_counts[uid] = completed_counts.get(uid, 0) + 1
        if uid not in last_module_by_user_id:
            last_module_by_user_id[uid] = mp.module
            last_module_completed_at_by_user_id[uid] = mp.completed_at

    students_progress = []
    completed_students_count = 0

    for user in users:
        uid = user.id
        assignment = assignments_by_user_id.get(uid)
        is_self_enrolled = uid in self_enrolled_ids

        if assignment is not None:
            if assignment.group_assignment_id and assignment.group_assignment.group:
                access_type = "group"
                access_label = f"Группа: {assignment.group_assignment.group.name}"
            else:
                access_type = "personal"
                access_label = "Личное назначение"
        else:
            access_type = "self"
            access_label = "Самозапись"

        completed_modules = completed_counts.get(uid, 0)
        cp = course_progress_by_user_id.get(uid)
        cp_completed_at = cp.completed_at if cp is not None else None
        last_module = last_module_by_user_id.get(uid)
        last_module_completed_at = last_module_completed_at_by_user_id.get(uid)

        is_completed = bool(
            cp_completed_at is not None
            or (total_modules > 0 and completed_modules >= total_modules)
        )
        completed_at = cp_completed_at or (
            last_module_completed_at if is_completed else None
        )

        if total_modules > 0:
            progress_percent = min(
                100, max(0, int(round(completed_modules * 100 / total_modules)))
            )
        else:
            progress_percent = 100 if is_completed else 0

        if is_completed:
            completed_students_count += 1

        students_progress.append(
            {
                "user": user,
                "full_name": user.get_full_name().strip(),
                "access_type": access_type,
                "access_label": access_label,
                "is_self_enrolled": is_self_enrolled,
                "has_assignment": assignment is not None,
                "completed_modules": completed_modules,
                "total_modules": total_modules,
                "progress_percent": progress_percent,
                "last_module": last_module,
                "last_module_completed_at": last_module_completed_at,
                "is_completed": is_completed,
                "completed_at": completed_at,
            }
        )

    return {
        "total_modules": total_modules,
        "completed_students_count": completed_students_count,
        "students_progress": students_progress,
    }
