from django.apps import AppConfig
from watson import search as watson


class CoursesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "courses"

    def ready(self):
        Course = self.get_model("Course")
        # Индексируем заголовок и описание курса
        watson.register(Course, fields=("title", "overview"))

        # Подключаем сигналы для синхронизации назначений групп
        import courses.signals  # noqa: F401
