# Generated by Django 4.1.4 on 2023-02-27 13:49

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('courses', '0006_alter_content_content_type_alter_content_module_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='content',
            name='content_type',
            field=models.ForeignKey(limit_choices_to={'model__in': ('text', 'video', 'image', 'file', 'htmltext', 'task', 'quiz')}, on_delete=django.db.models.deletion.CASCADE, to='contenttypes.contenttype'),
        ),
        migrations.CreateModel(
            name='Quiz',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=250, verbose_name='Название')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
                ('topic', models.CharField(max_length=120, verbose_name='Тема теста')),
                ('number_of_questions', models.IntegerField(verbose_name='Количество вопросов')),
                ('time', models.IntegerField(blank=True, help_text='Необязательно', null=True, verbose_name='Время на тест в минутах')),
                ('deadline', models.DateTimeField(blank=True, help_text='Необязательно', null=True, verbose_name='Срок сдачи')),
                ('required_score_to_pass', models.IntegerField(help_text='В процентах %', verbose_name='Требуемый результат для прохождения теста')),
                ('difficulty', models.CharField(choices=[('easy', 'легкий'), ('medium', 'средний'), ('hard', 'сложный')], max_length=6, verbose_name='Сложность')),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='%(class)s_related', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Quizes',
            },
        ),
        migrations.CreateModel(
            name='Question',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=200, verbose_name='Вопрос')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('quiz', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='questions', to='courses.quiz')),
            ],
        ),
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('text', models.CharField(max_length=200, verbose_name='Вариант ответа')),
                ('correct', models.BooleanField(default=False, verbose_name='Правильный вариант')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('question', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='answers', to='courses.question')),
            ],
        ),
    ]
