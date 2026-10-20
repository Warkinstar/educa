from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission


class Command(BaseCommand):
    help = "Настраивает группу 'Преподаватели' и привязывает к ней права курсов."

    def handle(self, *args, **options):
        courses_permissions = list(Permission.objects.filter(content_type__app_label="courses"))
        if not courses_permissions:
            self.stdout.write(self.style.WARNING("Права приложения 'courses' не найдены."))
            return

        group, created = Group.objects.get_or_create(name="Преподаватели")
        group.permissions.set(courses_permissions)
        status_text = "создана" if created else "обновлена"
        self.stdout.write(
            self.style.SUCCESS(
                f"Группа 'Преподаватели' успешно {status_text} с {len(courses_permissions)} правами."
            )
        )
