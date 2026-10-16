from django.test import TestCase
from django.urls import reverse
# почистил дублирующие импорты User и reverse, оставил get_user_model
from django.contrib.auth import get_user_model
from django.contrib.auth.models import (
    Group,
    AnonymousUser,
)
from courses.models import Course, Subject

# определяем модель пользователя через get_user_model()
User = get_user_model()


class PagesTests(TestCase):
    def setUp(self):
        # используем переменную User вместо длинной цепочки get_user_model()
        self.user = User.objects.create_user(
            username="testuser", email="testuser@example.com", password="testpass123"
        )
        self.anon_user = AnonymousUser()
        self.subject = Subject.objects.create(title="title", slug="title")
        self.course = Course.objects.create(
            subject=self.subject,
            owner=self.user,
            title="Математика",
            slug="matematika",
            overview="Best course",
        )

    def test_course_list_view(self):
        response = self.client.get(reverse("course_list"))
        # добавлен ведущий слэш '/no-response/', чтобы избежать некорректного пути
        no_response = self.client.get("/no-response/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(no_response.status_code, 404)
        self.assertEqual(self.course.title, "Математика")

    def test_course_detail_view_for_logged_out_user(self):
        # убрана строка self.client.login(email="") т.к. клиент и так анонимен
        response = self.client.get(reverse("course_detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Математика")
        self.assertContains(response, "Зарегистрируйтесь чтобы записаться")

    def test_course_detail_view_for_logged_in_user(self):
        # исправлен вход через username='testuser', так как по умолчанию вход идёт по username
        self.client.login(username="testuser", password="testpass123")
        response = self.client.get(reverse("course_detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Математика")
        self.assertContains(response, "Подписаться")


# ==============================================================================
# ВЕСЬ БЛОК НИЖЕ — ЭТО НОВЫЙ КЛАСС ТЕСТОВ ДЛЯ ПРОВЕРКИ СУПЕРПОЛЬЗОВАТЕЛЯ
# ==============================================================================
class ManageCourseAccessTests(TestCase):
    """
    Тестирование разграничения прав доступа.
    Проверяем, что управление курсами доступно НЕ конкретному юзеру,
    а СТРОГО любому аккаунту с флагом is_superuser=True.
    """
    def setUp(self):
        # Создаём обычного зарегистрированного пользователя (студента)
        self.regular_user = User.objects.create_user(
            username="regular_student",
            email="student@example.com",
            password="testpass123",
        )

        # Создаём произвольного суперпользователя (is_superuser=True)
        self.superuser = User.objects.create_superuser(
            username="random_admin",
            email="admin@example.com",
            password="testpass123",
        )

        # Получаем URL страницы управления курсами (/course/mine/)
        self.manage_url = reverse("manage_course_list")

    # Проверка №1 — Анонимный гость
    def test_anonymous_user_cannot_access_manage_courses(self):
        """Проверяю, что анонимного пользователя перенаправляет на страницу входа (302)"""
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login/", response.url)

    # Проверка №2 — Обычный залогиненный пользователь
    def test_regular_user_cannot_access_manage_courses(self):
        """Проверяю, что обычный пользователь получает отказ (403 Forbidden или 302 редирект), а не 200 OK"""
        self.client.login(username="regular_student", password="testpass123")
        response = self.client.get(self.manage_url)
        self.assertIn(
            response.status_code,
            [403, 302],
            f"Ошибка: обычный пользователь не должен открывать управление курсами! Получен код: {response.status_code}",
        )

    # Проверка №3 — Суперпользователь
    def test_superuser_can_access_manage_courses(self):
        """Проверяю, что суперпользователь успешно получает доступ (200 OK) и загружает нужный шаблон"""
        self.client.login(username="random_admin", password="testpass123")
        response = self.client.get(self.manage_url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "courses/manage/course/list.html")