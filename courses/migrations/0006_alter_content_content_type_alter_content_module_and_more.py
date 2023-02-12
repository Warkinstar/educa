# Generated by Django 4.1.4 on 2023-02-05 13:22

from django.conf import settings
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import django_quill.fields
import tinymce.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('contenttypes', '0002_remove_content_type_name'),
        ('courses', '0005_htmltext'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='content_type',
            field=models.ForeignKey(limit_choices_to={'model__in': ('text', 'video', 'image', 'file', 'htmltext', 'task')}, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.AlterField(
            model_name='content',
            name='module',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='contents', to='courses.module'),
        ),
        migrations.AlterField(
            model_name='file',
            name='file',
            field=models.FileField(upload_to='files/', verbose_name='Файл'),
        ),
        migrations.AlterField(
            model_name='htmltext',
            name='content',
            field=tinymce.models.HTMLField(verbose_name='Редактор'),
        ),
        migrations.CreateModel(
            name='Task',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250, verbose_name='Название')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('content', django_quill.fields.QuillField(verbose_name='Инструкции')),
                ('file', models.FileField(blank=True, help_text='Если требуется прикрепите файл', upload_to='tasks/', verbose_name='Файл')),
                ('max_score', models.PositiveIntegerField(blank=True, default=100, help_text='Укажите максимальный балл, который может получить студент за это задание от 0 до 100 (по умолчанию 100)', validators=[django.core.validators.MaxValueValidator(limit_value=100)], verbose_name='Маскимальный балл')),
                ('deadline', models.DateTimeField(blank=True, help_text='Необязательно', null=True, verbose_name='Срок сдачи')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_related', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
