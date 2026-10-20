"""
Сервисный слой управления назначениями курсов.

Правило разрешения конфликтов назначений:
1. В базе данных обеспечивается строго одно активное назначение пользователя на курс
   благодаря ограничению UniqueConstraint(fields=["course", "user"], condition=Q(is_active=True)).
2. Личное назначение (напрямую пользователю) имеет высший приоритет над групповым.
3. Если курс назначается группе (или пользователь добавляется в группу), но у него уже
   есть действующее активное назначение на этот же курс (личное либо через другую группу),
   новое назначение не создается, а текущее остается без изменений.
4. При прямом назначении через `assign_course_to_user`, если активное назначение уже
   существует, выбрасывается ValidationError с понятным текстом для формы/UI.
"""

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from .models import Course, CourseAssignment, CourseGroupAssignment, StudyGroup


def assign_course_to_user(course, user, assigned_by, activated_at=None, due_date=None, notes=""):
    """
    Создает личное назначение курса пользователю.
    Если у пользователя уже есть активное назначение на этот курс,
    выбрасывает ValidationError.
    """
    if activated_at and due_date and due_date < activated_at:
        raise ValidationError({"due_date": "Срок прохождения не может быть раньше даты активации."})

    existing_active = CourseAssignment.objects.filter(
        course=course,
        user=user,
        is_active=True,
    ).first()

    if existing_active:
        source = existing_active.assignment_source
        raise ValidationError(
            f"У пользователя {user.get_full_name() or user.username} уже есть активное назначение на этот курс ({source})."
        )

    return CourseAssignment.objects.create(
        course=course,
        user=user,
        group_assignment=None,
        activated_at=activated_at,
        due_date=due_date,
        is_active=True,
        assigned_by=assigned_by,
        notes=notes,
    )


def assign_course_to_group(course, group, assigned_by, activated_at=None, due_date=None, notes=""):
    """
    Создает групповое назначение курса и личные назначения всем участникам группы,
    у которых еще нет активного назначения на этот курс.
    """
    if activated_at and due_date and due_date < activated_at:
        raise ValidationError({"due_date": "Срок прохождения не может быть раньше даты активации."})

    with transaction.atomic():
        # Если назначение уже существовало, выбрасываем ошибку валидации (вместо падения БД)
        if CourseGroupAssignment.objects.filter(course=course, group=group).exists():
            raise ValidationError("Этот курс уже назначен данной группе. Измените существующее назначение.")

        group_assignment = CourseGroupAssignment.objects.create(
            course=course,
            group=group,
            assigned_by=assigned_by,
            activated_at=activated_at,
            due_date=due_date,
            is_active=True,
            notes=notes,
        )

        for user in group.users.all():
            has_active = CourseAssignment.objects.filter(
                course=course,
                user=user,
                is_active=True,
            ).exists()
            if not has_active:
                CourseAssignment.objects.create(
                    course=course,
                    user=user,
                    group_assignment=group_assignment,
                    activated_at=activated_at,
                    due_date=due_date,
                    is_active=True,
                    assigned_by=assigned_by,
                    notes=notes,
                )

        return group_assignment


def update_group_assignment(group_assignment, activated_at=None, due_date=None, is_active=None, notes=None):
    """
    Обновляет даты, статус и заметки группового назначения
    и синхронизирует изменения во все активные личные назначения этой группы.
    """
    new_activated_at = activated_at if activated_at is not None else group_assignment.activated_at
    new_due_date = due_date if due_date is not None else group_assignment.due_date

    if new_activated_at and new_due_date and new_due_date < new_activated_at:
        raise ValidationError({"due_date": "Срок прохождения не может быть раньше даты активации."})

    with transaction.atomic():
        if activated_at is not None:
            group_assignment.activated_at = activated_at
        if due_date is not None:
            group_assignment.due_date = due_date
        if is_active is not None:
            group_assignment.is_active = is_active
        if notes is not None:
            group_assignment.notes = notes

        group_assignment.full_clean()
        group_assignment.save()

        # Обновляем связанные личные назначения
        personal_assignments = group_assignment.individual_assignments.all()
        for assignment in personal_assignments:
            if activated_at is not None:
                assignment.activated_at = activated_at
            if due_date is not None:
                assignment.due_date = due_date
            if is_active is not None:
                assignment.is_active = is_active
            if notes is not None and notes.strip():
                assignment.notes = notes
            assignment.save()

        return group_assignment


def deactivate_group_assignment(group_assignment):
    """
    Деактивирует групповое назначение и все созданные через него личные назначения.
    """
    with transaction.atomic():
        group_assignment.is_active = False
        group_assignment.save(update_fields=["is_active"])

        group_assignment.individual_assignments.filter(is_active=True).update(is_active=False)
        return group_assignment


def sync_group_membership(group):
    """
    Синхронизирует состав участников группы со всеми ее активными назначениями:
    - новым участникам создает личные назначения (если нет другого активного назначения);
    - у удаленных участников деактивирует личные назначения этой группы.
    """
    active_group_assignments = group.course_assignments.filter(is_active=True)
    if not active_group_assignments.exists():
        return

    current_users = set(group.users.all())

    with transaction.atomic():
        for g_assignment in active_group_assignments:
            course = g_assignment.course
            existing_individual = g_assignment.individual_assignments.all()
            assigned_users = set(item.user for item in existing_individual)

            # 1. Новые участники
            new_users = current_users - assigned_users
            for user in new_users:
                has_active = CourseAssignment.objects.filter(
                    course=course,
                    user=user,
                    is_active=True,
                ).exists()
                if not has_active:
                    CourseAssignment.objects.create(
                        course=course,
                        user=user,
                        group_assignment=g_assignment,
                        activated_at=g_assignment.activated_at,
                        due_date=g_assignment.due_date,
                        is_active=True,
                        assigned_by=g_assignment.assigned_by,
                        notes=f"Добавлен через группу: {group.name}",
                    )

            # 2. Удаленные участники
            removed_users = assigned_users - current_users
            if removed_users:
                g_assignment.individual_assignments.filter(
                    user__in=removed_users,
                    is_active=True,
                ).update(is_active=False)
