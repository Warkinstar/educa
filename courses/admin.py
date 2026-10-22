from django.contrib import admin
from .models import (
    Subject, Course, Module, Task, Content, Quiz, Answer, Question,
    StudyGroup, CourseGroupAssignment, CourseAssignment
)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ["title", "slug"]
    prepopulated_fields = {"slug": ("title",)}


class ModuleInline(admin.StackedInline):
    model = Module


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ["title", "subject", "is_public", "is_active", "created"]
    list_filter = ["is_public", "is_active", "created", "subject"]
    list_editable = ["is_public", "is_active"]
    search_fields = ["title", "overview"]
    prepopulated_fields = {"slug": ("title",)}
    inlines = [ModuleInline]
    filter_horizontal = ["students"]


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ["course", "title", "module_price"]


@admin.register(StudyGroup)
class StudyGroupAdmin(admin.ModelAdmin):
    list_display = ["name", "created_by", "created", "get_members_count"]
    search_fields = ["name", "description"]
    filter_horizontal = ["users"]

    @admin.display(description="Участников")
    def get_members_count(self, obj):
        return obj.users.count()


@admin.register(CourseGroupAssignment)
class CourseGroupAssignmentAdmin(admin.ModelAdmin):
    list_display = ["course", "group", "is_active", "activated_at", "due_date", "assigned_by", "assigned_at"]
    list_filter = ["is_active", "assigned_at"]
    search_fields = ["course__title", "group__name"]
    raw_id_fields = ["course", "group", "assigned_by"]


@admin.register(CourseAssignment)
class CourseAssignmentAdmin(admin.ModelAdmin):
    list_display = ["course", "user", "assignment_type", "is_active", "activated_at", "due_date", "assigned_at"]
    list_filter = ["is_active", "group_assignment__group"]
    search_fields = ["course__title", "user__username", "user__email"]
    raw_id_fields = ["course", "user", "group_assignment", "assigned_by"]

    @admin.display(description="Тип назначения")
    def assignment_type(self, obj):
        if obj.group_assignment:
            return f"Группа: {obj.group_assignment.group.name}"
        return "Индивидуальное"


admin.site.register(Task)
admin.site.register(Quiz)
admin.site.register(Answer)


class AnswerInline(admin.TabularInline):
    model = Answer


@admin.register(Question)
class QuestionAnswer(admin.ModelAdmin):
    list_display = ["quiz", "text"]
    inlines = [AnswerInline]
