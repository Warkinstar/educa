import inspect
import io
import json
import pathlib
import uuid
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image as PilImage

import comments.views as comment_views
import courses.views as course_views
from comments.models import Comment, CommentFile
from courses.models import Course, CourseProgress, Module, ModuleProgress, Subject
from courses.services.analytics import get_course_analytics_data

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
        perms = Permission.objects.filter(
            codename__in=["add_course", "change_course", "delete_course", "view_course"]
        )
        self.teacher.user_permissions.add(*perms)

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

    def test_course_detail_renders_clean_comments_and_sweetalert_in_comments_template(self):
        self.client.force_login(self.student)
        url = reverse(
            "student_course_detail_module",
            kwargs={"pk": self.course.pk, "module_id": self.module.pk},
        )
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        # 1. SweetAlert2 v11 подключён в шаблоне комментариев, а не в <head> base.html
        head_end = html.find("</head>")
        swal_css_pos = html.find("sweetalert2@11/dist/sweetalert2.min.css")
        swal_js_pos = html.find("cdn.jsdelivr.net/npm/sweetalert2@11")
        self.assertNotEqual(swal_css_pos, -1)
        self.assertNotEqual(swal_js_pos, -1)
        self.assertGreater(swal_js_pos, head_end)
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

        # 4. Карточка выбора получателей (notify_user_card.html) отрендерена с участниками
        self.assertIn(f'id="notify-users-card-', html)
        self.assertIn("Иван Преподавателев", html)

        # 5. Контейнер не содержит <script type="module"> (исключает SyntaxError при HTMX swap)
        self.assertNotIn('<script type="module">', html)
        self.assertIn(f'id="comments-and-form-section-{self.module.public_id}"', html)
        self.assertIn('hx-swap="outerHTML"', html)

    def test_teacher_module_content_list_renders_comments_and_modals_correctly(self):
        self.client.force_login(self.teacher)
        url = reverse("module_content_list", kwargs={"module_id": self.module.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        html = response.content.decode("utf-8")

        self.assertNotIn("Чат курса", html)
        self.assertIn(f'id="comments-and-form-section-{self.module.public_id}"', html)
        # Карточка получателей присутствует на странице модуля у преподавателя
        self.assertIn("id=\"notify-users-card-", html)
        self.assertIn("Пётр Студентов", html)

        # Quill и TinyMCE подключены один раз на странице модуля, без init_tinymce.js
        self.assertIn("tinymce/tinymce.min.js", html)
        self.assertNotIn("init_tinymce.js", html)
        self.assertEqual(html.count("django_quill/django_quill.js"), 1)

        # Модалка настройки модулей имеет .modal-header и .modal-body#modal-body-modules-course
        self.assertIn('class="modal-body" id="modal-body-modules-course"', html)

        # Обработчик closeModal навешивается ровно один раз
        self.assertEqual(html.count("addEventListener('closeModal'"), 1)

    @patch("comments.tasks.send_comment_notification_email_task.delay")
    def test_comment_create_preserves_notify_users_and_uses_get_absolute_url(self, mock_delay):
        # CommentCreateView не должен импортировать courses.Module
        views_source = inspect.getsource(comment_views)
        self.assertNotIn("courses.models", views_source)
        self.assertNotIn("isinstance(", views_source)

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

        # 1. Ошибка валидации (пустой текст): карточка notify_users не должна пропадать
        err_response = self.client.post(
            create_url,
            data={
                "text": "",
                "upload_session_id": str(upload_session_id),
            },
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(err_response.status_code, 200)
        err_html = err_response.content.decode("utf-8")
        self.assertIn(f'id="notify-users-card-{upload_session_id}"', err_html)
        self.assertIn("Иван Преподавателев", err_html)

        # 2. Успешное создание комментария с уведомлением выбранного участника
        response = self.client.post(
            create_url,
            data={
                "text": "Первый тестовый комментарий к модулю!",
                "upload_session_id": str(upload_session_id),
                "notify_participants": "on",
                "comment_notify_users": [str(self.teacher.pk)],
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
        # Карточка выбора получателей остаётся после отправки комментария
        self.assertIn('id="notify-users-card-', html)
        self.assertIn("Иван Преподавателев", html)

        # Ссылка в письме сформирована через Module.get_absolute_url()
        self.assertTrue(mock_delay.called)
        call_kwargs = mock_delay.call_args.kwargs
        self.assertIn(self.module.get_absolute_url(), call_kwargs["comment_page_link"])

        # 3. Удаление комментария через comments:comment_delete
        delete_url = reverse("comments:comment_delete", kwargs={"public_id": comment.public_id})
        del_response = self.client.post(
            delete_url,
            data={"public_id": str(comment.public_id)},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(del_response.status_code, 200)
        self.assertEqual(del_response.content.decode("utf-8"), "")
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_content_modals_tinymce_quill_and_after_swap_sortable(self):
        self.client.force_login(self.teacher)

        # 1. TINYMCE_DEFAULT_CONFIG не захватывает все textarea и включает плагин image
        self.assertEqual(settings.TINYMCE_DEFAULT_CONFIG["selector"], "textarea.tinymce")
        self.assertIn("image", settings.TINYMCE_DEFAULT_CONFIG["plugins"])

        # 2. Модалка htmltext не рендерит form.media (нет init_tinymce.js), но содержит images_upload_handler
        htmltext_url = reverse(
            "module_content_create",
            kwargs={"module_id": self.module.pk, "model_name": "htmltext"},
        )
        resp_html = self.client.get(htmltext_url).content.decode("utf-8")
        self.assertNotIn("init_tinymce.js", resp_html)
        self.assertIn("images_upload_handler", resp_html)
        self.assertIn(reverse("upload_image", args=[self.module.pk]), resp_html)

        # 3. Модалка task не подгружает повторно django_quill.js и не содержит quillWidget.__quill
        task_url = reverse(
            "module_content_create",
            kwargs={"module_id": self.module.pk, "model_name": "task"},
        )
        resp_task = self.client.get(task_url).content.decode("utf-8")
        self.assertNotIn("django_quill.js", resp_task)
        self.assertNotIn("__quill", resp_task)

        # 4. Сохранение блока в модалке отправляет reinitSortable в HX-Trigger-After-Swap
        text_url = reverse(
            "module_content_create",
            kwargs={"module_id": self.module.pk, "model_name": "text"},
        )
        save_resp = self.client.post(
            text_url,
            data={"title": "Конспект", "content": "Текст блока"},
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(save_resp.status_code, 200)
        self.assertIn("HX-Trigger-After-Swap", save_resp.headers)
        after_swap = json.loads(save_resp.headers["HX-Trigger-After-Swap"])
        self.assertTrue(after_swap.get("reinitSortable"))

        # 5. Удалены старый form.html и функция upload_image
        old_template = pathlib.Path(settings.BASE_DIR) / "courses/templates/courses/manage/content/form.html"
        self.assertFalse(old_template.exists())
        self.assertFalse(hasattr(course_views, "upload_image"))

    def test_course_analytics_and_export_with_student_progress(self):
        m2 = Module.objects.create(course=self.course, title="Модуль 2", description="Второй")
        CourseProgress.objects.create(user=self.student, course=self.course)
        ModuleProgress.objects.create(user=self.student, module=self.module)

        data = get_course_analytics_data(self.course)
        self.assertEqual(data["total_students_count"], 1)
        self.assertEqual(data["total_modules_count"], 2)
        student_row = data["students_summary"][0]
        self.assertEqual(student_row["progress_percent"], 50)
        self.assertFalse(student_row["is_completed"])

        # Завершаем второй модуль -> 100%
        ModuleProgress.objects.create(user=self.student, module=m2)
        self.client.force_login(self.teacher)
        analytics_url = reverse("course_analytics", kwargs={"pk": self.course.pk})
        export_url = reverse("course_analytics_export", kwargs={"pk": self.course.pk})

        resp_page = self.client.get(analytics_url)
        self.assertEqual(resp_page.status_code, 200)
        self.assertIn("100%", resp_page.content.decode("utf-8"))

        resp_xlsx = self.client.get(export_url)
        self.assertEqual(resp_xlsx.status_code, 200)
        self.assertEqual(
            resp_xlsx["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

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
