from django.db import migrations


def create_instructor_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    courses_permissions = list(Permission.objects.filter(content_type__app_label="courses"))

    for group_name in ["Преподаватели", "Instructors"]:
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.set(courses_permissions)


def remove_instructor_groups(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=["Преподаватели", "Instructors"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("courses", "0010_module_module_price_alter_module_order"),
    ]

    operations = [
        migrations.RunPython(create_instructor_groups, remove_instructor_groups),
    ]

