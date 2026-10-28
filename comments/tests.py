import uuid

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from comments.models import Comment, CommentFile
from courses.models import Course, Module, Subject

User = get_user_model()


class UniversalCommentsIntegrationTests(TestCase):
    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher_user",
            email="teacher@example.com",
            password="testpassword123",
            first_name="Иван",
            last_name="Преподавателев",
        )
        self.student = User.objects.create_user(
            username="student_user",
            email="student@example.com",
            password="testpassword123",
            first_name="Пётр",
            last_name="Студентов",
        )
        self.subject = Subject.objects.create(title="Программирование", slug="programming")
        self.course = Course.objects.create(
            owner=self.teacher,
            subject=self.subject,
            title="Python Backend",
            slug="python-backend",
            overview="Описание курса",
            is_active=True,
            is_public=True,
        )
        self.course.students.add(self.student)
        self.module = Module.objects.create(
            course=self.course,
            title="Введение в Django",
            description="Модуль 1",
        )

    def test_course_detail_renders_clean_comments_and_sweetalert_order(self):
        self.client.force_login(self.student)
        url = reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        # 1. SweetAlert2 v11 подключён один раз и загружается строго до HTMX и Alpine.js
        swal_css_pos = html.find("sweetalert2@11/dist/sweetalert2.min.css")
        swal_js_pos = html.find("cdn.jsdelivr.net/npm/sweetalert2@11")
        htmx_js_pos = html.find("htmx.org@1.9.12")
        alpine_js_pos = html.find("alpinejs@3.13.10")

        self.assertNotEqual(swal_css_pos, -1)
        self.assertNotEqual(swal_js_pos, -1)
        self.assertLess(swal_js_pos, htmx_js_pos)
        self.assertLess(swal_js_pos, alpine_js_pos)
        self.assertEqual(html.count('src="https://cdn.jsdelivr.net/npm/sweetalert2@11"'), 1)

        # 2. В detail.html нет сломанных комментариев и скрыт старый «Чат курса»
        self.assertNotIn("{# Блок универсальных комментариев модуля", html)
        self.assertNotIn("Чат курса", html)
        self.assertNotIn(f"/chat/room/{self.course.pk}/", html)

        # 3. В x-data объявлены все реактивные свойства + comment_count
        expected_xdata_keys = [
            "reply_to:",
            "comment_reply_to_text:",
            "comment_reply_to_created_by_full_name:",
            "reply_to_anchor:",
            "notify_reply_to:",
            "notify_participants:",
            "mention:",
            "comment_message:",
            "comment_page_link:",
            "comment_subject:",
            "notify_users:",
            "comment_count:",
        ]
        for key in expected_xdata_keys:
            self.assertIn(key, html)

        # 4. Контейнер не содержит <script type="module"> (исключает SyntaxError при HTMX swap)
        self.assertNotIn('<script type="module">', html)
        self.assertIn(f'id="comments-and-form-section-{self.module.public_id}"', html)
        self.assertIn('hx-swap="outerHTML"', html)

    def test_teacher_module_content_list_renders_comments_and_hides_legacy_chat(self):
        self.client.force_login(self.teacher)
        url = reverse("module_content_list", kwargs={"module_id": self.module.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")
        self.assertNotIn("Чат курса", html)
        self.assertIn(f'id="comments-and-form-section-{self.module.public_id}"', html)

    def test_comment_create_reply_and_delete_via_htmx(self):
        self.client.force_login(self.student)
        upload_session_id = uuid.uuid4()
        create_url = reverse(
            "comments:comment_create",
            kwargs={
                "app_label": "courses",
                "model_name": "module",
                "public_id": self.module.public_id,
            },
        )

        # Создание комментария через HTMX
        response = self.client.post(
            create_url,
            data={
                "text": "Первый тестовый комментарий к модулю!",
                "upload_session_id": str(upload_session_id),
                "reply_to": "",
                "mention": "",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 1)
        comment = Comment.objects.first()

        html = response.content.decode("utf-8")
        self.assertIn("Первый тестовый комментарий к модулю!", html)
        self.assertIn("Пётр Студентов", html)
        self.assertIn("comment_count: 1", html)
        self.assertIn("Swal.fire", html)
        self.assertEqual(
            html.count(f'id="comments-and-form-section-{self.module.public_id}"'),
            1,
        )

        # Ответ на комментарий
        reply_response = self.client.post(
            create_url,
            data={
                "text": "Ответ преподавателя на вопрос студента",
                "upload_session_id": str(uuid.uuid4()),
                "reply_to": str(comment.pk),
                "mention": "",
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(reply_response.status_code, 200)
        self.assertEqual(Comment.objects.count(), 2)
        reply_html = reply_response.content.decode("utf-8")
        self.assertIn("comment_count: 2", reply_html)
        self.assertIn("Ответ преподавателя на вопрос студента", reply_html)

        # Удаление комментария через comments:comment_delete
        delete_url = reverse("comments:comment_delete", kwargs={"public_id": comment.public_id})
        del_response = self.client.post(
            delete_url,
            data={"public_id": str(comment.public_id)},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(del_response.status_code, 200)
        self.assertEqual(del_response.content.decode("utf-8"), "")
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_unrelated_file_upload_list_delete_and_download(self):
        self.client.force_login(self.student)
        session_id = uuid.uuid4()

        # 1. Загрузка временного файла
        upload_url = reverse(
            "comments:unrelated_comment_file_upload",
            kwargs={"app_label": "courses", "model_name": "module"},
        )
        sample_file = SimpleUploadedFile("notes.txt", b"Hello Educa comments!", content_type="text/plain")
        up_resp = self.client.post(
            upload_url,
            data={"upload_session_id": str(session_id), "file": sample_file},
        )
        self.assertEqual(up_resp.status_code, 200)
        self.assertEqual(up_resp.json()["status"], "ok")
        cfile = CommentFile.objects.get(upload_session_id=session_id)

        # 2. Получение списка временных файлов (с Swal.fire для удаления)
        list_url = reverse("comments:unrelated_comment_file_list")
        list_resp = self.client.get(list_url, data={"upload_session_id": str(session_id)})
        self.assertEqual(list_resp.status_code, 200)
        list_html = list_resp.content.decode("utf-8")
        self.assertIn("notes.txt", list_html)
        self.assertIn("Swal.fire", list_html)

        # 3. Удаление временного файла
        del_file_url = reverse("comments:unrelated_comment_file_delete", kwargs={"public_id": cfile.public_id})
        del_file_resp = self.client.post(del_file_url, HTTP_HX_REQUEST="true")
        self.assertEqual(del_file_resp.status_code, 200)
        self.assertFalse(CommentFile.objects.filter(pk=cfile.pk).exists())

        # 4. Загрузка нового файла, привязка к комментарию и скачивание
        sample_file_2 = SimpleUploadedFile("summary.txt", b"Attachment content", content_type="text/plain")
        self.client.post(upload_url, data={"upload_session_id": str(session_id), "file": sample_file_2})
        bound_file = CommentFile.objects.get(upload_session_id=session_id)

        create_url = reverse(
            "comments:comment_create",
            kwargs={
                "app_label": "courses",
                "model_name": "module",
                "public_id": self.module.public_id,
            },
        )
        self.client.post(
            create_url,
            data={"text": "Комментарий с файлом", "upload_session_id": str(session_id)},
            HTTP_HX_REQUEST="true",
        )
        bound_file.refresh_from_db()
        self.assertIsNotNone(bound_file.comment_id)

        download_url = reverse("comments:comment_file_download", kwargs={"public_id": bound_file.public_id})
        dl_resp = self.client.get(download_url)
        self.assertEqual(dl_resp.status_code, 200)
        dl_resp.close()
