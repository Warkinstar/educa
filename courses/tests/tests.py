from django.test import TestCase
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from django.shortcuts import reverse
from django.contrib.auth.models import (
    Group,
    AnonymousUser,
)
from courses.models import Course, Subject


class PagesTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
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
        no_response = self.client.get("no-response/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(no_response.status_code, 404)
        self.assertEqual(self.course.title, "Математика")

    def test_course_detail_view_for_logged_out_user(self):
        self.client.login(email="")
        response = self.client.get(reverse("course_detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Математика")
        self.assertContains(response, "Зарегистрируйтесь чтобы записаться")


    def test_course_detail_view_for_logged_in_user(self):
        self.client.login(email="testuser@example.com", password="testpass123")
        response = self.client.get(reverse("course_detail", kwargs={"slug": self.course.slug}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Математика")
        self.assertContains(response, "Подписаться")




