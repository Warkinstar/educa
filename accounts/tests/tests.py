from accounts.models import TeacherRequest
from django.test import Client, TestCase
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import reverse
from rest_framework import status


class TeacherRequestModelSignalViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username="testuser",
            email="testuser@email.com",
            password="testpass123",
        )

        self.teacher_request = TeacherRequest.objects.create(
            user=self.user,
            # status="pending",  # default value
        )

        self.user_without_teacher_request_model = get_user_model().objects.create_user(
            username="testuser_01",
            email="testuser_01@email.com",
            password="testpass123",
        )

        # Для проверки добавления/удаления пользователя в группу при смене
        # teacher_request.status approved/rejected соответственно
        self.group_name = "Преподаватели"
        Group.objects.create(name=self.group_name)

    def test_teacher_request_model_listing(self):
        self.assertEqual(self.teacher_request.user, self.user)
        # status by default is "pending"
        self.assertEqual(self.teacher_request.status, "pending")

    def test_check_teacher_group_request_post_save_signal(self):
        """
         Тест сигнала после сохранения модели выполняет проверки
         Если TeacherRequest.status approved добавить пользователя в группу Преподаватели
        Если TeacherRequest.status rejected удалить его из группы или ничего не делать
        """
        # Пользователь не состоит в группе
        self.assertEqual(self.user.groups.filter(name=self.group_name).exists(), False)
        # Изменяем self.teacher_request.status на approved
        self.teacher_request.status = "approved"
        self.teacher_request.save()
        self.assertEqual(self.teacher_request.status, "approved")
        # Пользователя добавлен в группу
        self.assertEqual(self.user.groups.filter(name=self.group_name).exists(), True)
        # teacher_request.status = rejected - убрать пользователя из группы
        self.teacher_request.status = "rejected"
        self.teacher_request.save()
        self.assertEqual(self.user.groups.filter(name=self.group_name).exists(), False)

    def test_request_teacher_status_view(self):
        """Тест представления"""
        # Временный пользователь

        bad_response = self.client.post(reverse("request_teacher_status"))
        # Перенаправили неавторизованного пользователя на login page
        self.assertEqual(bad_response.status_code, status.HTTP_302_FOUND)

        # Вход в аккаунт, пользователь не имеет TeacherRequest связанный экземпляр
        self.client.login(email="testuser_01@email.com", password="testpass123")

        # Get request не разрешен к этому представлению
        get_response = self.client.get(reverse("request_teacher_status"))
        self.assertEqual(get_response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

        # После post запроса был выполнен редирект
        post_response = self.client.post(reverse("request_teacher_status"))
        self.assertEqual(post_response.status_code, status.HTTP_302_FOUND)

        redirect_url = post_response.url  # Адрес редиректа
        expected_url = reverse("account_email")  # Ожидаемый адрес редиректа
        self.assertEqual(redirect_url, expected_url)

        # Теперь изначально не имея пользователь имеет связанную TeacherRequest со статусом "pending"
        self.assertEqual(
            self.user_without_teacher_request_model.teacherrequest.status, "pending"
        )
