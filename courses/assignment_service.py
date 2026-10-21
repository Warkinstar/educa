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
    Создает или реактивирует групповое назначение курса и личные назначения участникам группы:
    - Если назначение уже активно — выбрасывает ValidationError.
    - Если пара (course, group) существовала, но была деактивирована — реактивирует ее с новыми датами
      и обновляет/создает личные назначения участникам группы (через sync_group_membership).
    - Если назначения не было — создает новое.
    """
    if activated_at and due_date and due_date < activated_at:
        raise ValidationError({"due_date": "Срок прохождения не может быть раньше даты активации."})

    with transaction.atomic():
        existing = CourseGroupAssignment.objects.filter(course=course, group=group).first()

        if existing:
            if existing.is_active:
                raise ValidationError("Этот курс уже активно назначен данной группе. Измените даты существующего назначения.")
            
            # Реактивация существующего деактивированного назначения с новыми параметрами
            existing.is_active = True
            existing.activated_at = activated_at
            existing.due_date = due_date
            existing.assigned_by = assigned_by
            existing.notes = notes
            existing.save(update_fields=['is_active', 'activated_at', 'due_date', 'assigned_by', 'notes'])
            group_assignment = existing
        else:
            group_assignment = CourseGroupAssignment.objects.create(
                course=course,
                group=group,
                assigned_by=assigned_by,
                activated_at=activated_at,
                due_date=due_date,
                is_active=True,
                notes=notes,
            )

        # Синхронизируем участников: всем активным участникам выдастся/реактивируется личный доступ
        sync_group_membership(group)

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

def deactivate_user_assignment(assignment):
    """
    Деактивирует индивидуальное назначение курса пользователю.
    """
    assignment.is_active = False
    assignment.save(update_fields=["is_active"])
    return assignment

def sync_group_membership(group):
    """
    Синхронизирует состав участников группы со всеми ее активными назначениями:
    - Новые или вернувшиеся участники группы:
      * Если у пользователя уже есть неактивное личное назначение в рамках этого g_assignment,
        оно реактивируется (is_active=True), а даты актуализируются под текущие даты группы
        (при условии, что у пользователя нет другого активного назначения на этот курс).
      * Если назначения не было вовсе — создается новое CourseAssignment.
    - Удаленные участники группы:
      * Их личные назначения в рамках этого g_assignment деактивируются (is_active=False).
    - Ограничение: один пользователь не может иметь более одного активного назначения на курс.
    """
    active_group_assignments = group.course_assignments.filter(is_active=True)
    if not active_group_assignments.exists():
        return

    current_users = set(group.users.all())

    with transaction.atomic():
        for g_assignment in active_group_assignments:
            course = g_assignment.course
            
            # Активные назначения пользователей в рамках этой группы
            active_individual = g_assignment.individual_assignments.filter(is_active=True)
            active_assigned_users = set(item.user for item in active_individual)

            # 1. Пользователи, у которых сейчас нет активного назначения через эту группу
            users_to_assign = current_users - active_assigned_users

            for user in users_to_assign:
                # Проверяем, нет ли у пользователя другого активного назначения на этот курс
                has_other_active = CourseAssignment.objects.filter(
                    course=course,
                    user=user,
                    is_active=True,
                ).exclude(group_assignment=g_assignment).exists()

                if has_other_active:
                    continue

                # Ищем существовавшее ранее назначение по этой же связке
                existing_assignment = g_assignment.individual_assignments.filter(user=user).first()

                if existing_assignment:
                    # Реактивируем существующее назначение и обновляем даты под группу
                    existing_assignment.is_active = True
                    existing_assignment.activated_at = g_assignment.activated_at
                    existing_assignment.due_date = g_assignment.due_date
                    existing_assignment.assigned_by = g_assignment.assigned_by
                    existing_assignment.notes = f"Реактивирован через группу: {group.name}"
                    existing_assignment.save(update_fields=[
                        'is_active', 'activated_at', 'due_date', 'assigned_by', 'notes'
                    ])
                else:
                    # Создаем новое назначение
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

            # 2. Удаленные участники: деактивируем их назначения
            removed_users = active_assigned_users - current_users
            if removed_users:
                g_assignment.individual_assignments.filter(
                    user__in=removed_users,
                    is_active=True,
                ).update(is_active=False)