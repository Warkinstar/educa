from datetime import timedelta
from django.utils import timezone
from django.test import TestCase, RequestFactory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.messages.storage.fallback import FallbackStorage

from courses.models import Course, Subject, StudyGroup, CourseGroupAssignment, CourseAssignment
from courses.assignment_service import (
    assign_course_to_user,
    assign_course_to_group,
    deactivate_group_assignment,
)
from courses.views import (
    CourseGroupsModalView,
    CourseGroupAssignmentDeactivateView,
)

User = get_user_model()


class CourseAssignmentsTestCase(TestCase):
    def setUp(self):
        self.instructor = User.objects.create_user(username="instructor", password="password123")
        # Выдаем права на редактирование курса
        perm = Permission.objects.get(codename="change_course")
        self.instructor.user_permissions.add(perm)
        assign_perm = Permission.objects.filter(codename="manage_course_assignments").first()
        if assign_perm:
            self.instructor.user_permissions.add(assign_perm)

        self.student1 = User.objects.create_user(username="student1", password="password123")
        self.student2 = User.objects.create_user(username="student2", password="password123")
        self.student3 = User.objects.create_user(username="student3", password="password123")

        self.subject = Subject.objects.create(title="Тестовый предмет", slug="test-subject")
        self.course = Course.objects.create(
            owner=self.instructor,
            subject=self.subject,
            title="Тестовый курс",
            slug="test-course",
            overview="Описание",
            is_public=False,
            is_active=True,
        )
        self.group = StudyGroup.objects.create(name="Группа А", created_by=self.instructor)
        self.group.users.add(self.student1, self.student2)
        self.rf = RequestFactory()

    def test_direct_user_assignment_lifecycle(self):
        # Назначение курса пользователю
        assignment = assign_course_to_user(
            course=self.course,
            user=self.student3,
            assigned_by=self.instructor,
            notes="Индивидуальный доступ",
        )
        self.assertTrue(assignment.is_active)
        has_access, _ = self.course.can_user_access(self.student3)
        self.assertTrue(has_access)

        # Деактивация назначения
        assignment.is_active = False
        assignment.save()
        assignment.refresh_from_db()
        self.assertFalse(assignment.is_active)
        has_access, _ = self.course.can_user_access(self.student3)
        self.assertFalse(has_access)

    def test_group_assignment_lifecycle_and_signals(self):
        # Назначение группе
        group_assignment = assign_course_to_group(
            course=self.course,
            group=self.group,
            assigned_by=self.instructor,
        )
        self.assertTrue(group_assignment.is_active)
        self.assertTrue(self.course.can_user_access(self.student1)[0])
        self.assertTrue(self.course.can_user_access(self.student2)[0])
        self.assertFalse(self.course.can_user_access(self.student3)[0])

        # Сигнал добавления нового студента в группу (post_add)
        self.group.users.add(self.student3)
        self.assertTrue(self.course.can_user_access(self.student3)[0])

        # Сигнал исключения студента из группы (post_remove)
        self.group.users.remove(self.student1)
        self.assertFalse(self.course.can_user_access(self.student1)[0])

        # Деактивация группового назначения
        deactivate_group_assignment(group_assignment)
        group_assignment.refresh_from_db()
        self.assertFalse(group_assignment.is_active)
        self.assertFalse(self.course.can_user_access(self.student2)[0])
        self.assertFalse(self.course.can_user_access(self.student3)[0])

    def test_course_groups_modal_view_post_and_deactivate(self):
        # Проверка создания через view
        req = self.rf.post(f"/courses/modal/{self.course.pk}/groups/", {
            "group": self.group.pk,
            "notes": "Назначение через UI",
        })
        req.user = self.instructor
        setattr(req, "session", {})
        setattr(req, "_messages", FallbackStorage(req))

        response = CourseGroupsModalView.as_view()(req, pk=self.course.pk)
        self.assertEqual(response.status_code, 200)

        group_assignment = CourseGroupAssignment.objects.filter(course=self.course, group=self.group).first()
        self.assertIsNotNone(group_assignment)
        self.assertTrue(group_assignment.is_active)

        # Проверка деактивации через view
        req_deact = self.rf.post(f"/courses/modal/group-assignment/{group_assignment.pk}/deactivate/")
        req_deact.user = self.instructor
        setattr(req_deact, "session", {})
        setattr(req_deact, "_messages", FallbackStorage(req_deact))

        resp_deact = CourseGroupAssignmentDeactivateView.as_view()(req_deact, pk=group_assignment.pk)
        self.assertEqual(resp_deact.status_code, 200)
        group_assignment.refresh_from_db()
        self.assertFalse(group_assignment.is_active)
