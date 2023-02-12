from django.contrib import admin
from .models import Subject, Course, Module, Task, Content

@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}


class ModuleInline(admin.StackedInline):
    model = Module


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "created"]
    list_filter = ["created", "subject"]
    search_fields = ["title", "overview"]
    inlines = [ModuleInline]



admin.site.register(Task)  # Удаляя Task, удаляется Content, Answers и сам Task
# admin.site.register(Content)  # Удаляя content ничего связанного не удаляется
