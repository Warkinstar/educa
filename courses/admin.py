from django.contrib import admin
from .models import Subject, Course, Module, Task, Content, Quiz, Answer, Question


"""Subject"""


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}


"""ModuleInline - Course"""


class ModuleInline(admin.StackedInline):
    model = Module


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "created"]
    list_filter = ["created", "subject"]
    search_fields = ["title", "overview"]
    inlines = [ModuleInline]


"""Module itself"""


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["course", "title", "module_price"]


"""Task"""

admin.site.register(Task)  # Удаляя Task, удаляется Content, Answers и сам Task
# admin.site.register(Content)  # Удаляя content ничего связанного не удаляется

"""Quiz"""

admin.site.register(Quiz)

"""Answer - AnswerInline - QuestionAnswer"""

admin.site.register(Answer)


class AnswerInline(admin.TabularInline):
    model = Answer


@admin.register(Question)
class QuestionAnswer(admin.ModelAdmin):
    list_display = ["quiz", "text"]
    inlines = [AnswerInline]
