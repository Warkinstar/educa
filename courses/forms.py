from courses.models import StudyGroup, CourseGroupAssignment
from django import forms
from django.contrib.auth import get_user_model
from django.db.models import Case, IntegerField, Q, Value, When
from django_select2 import forms as s2forms
from django_select2.forms import ModelSelect2MultipleWidget
from django.utils.text import slugify
from unidecode import unidecode
from .models import Course, Module, Subject
from django.core.exceptions import ValidationError

User = get_user_model()

# Общие атрибуты select2 из референса
general_select2_attrs = {
    "data-minimum-input-length": 0,
    "data-placeholder": "Выберите тему",
    "data-close-on-select": "true",
    "data-allow-clear": "true",
    "data-language": "ru",
    "class": "form-control",
}

class SubjectSelect2Widget(s2forms.ModelSelect2Widget):
    search_fields = ["title__icontains"]


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ["title"]

    def clean_title(self):
        title = self.cleaned_data.get("title", "").strip()
        if Subject.objects.filter(title__iexact=title).exists():
            raise forms.ValidationError("Тема с таким названием уже существует.")
        return title

class UserSelect2MultipleWidget(ModelSelect2MultipleWidget):
    model = User
    search_fields = [
        "first_name__icontains",
        "last_name__icontains",
        "username__icontains",
        "email__icontains",
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        # Если передан course_id, исключаем или фильтруем по связи с курсом
        course_id = dependent_fields.pop("course_id", None)
        qs = super().filter_queryset(request, term, queryset=queryset, **dependent_fields)
        if course_id:
            # Исключаем пользователей, которые уже записаны на данный курс
            qs = qs.exclude(courses_joined__id=course_id)
        return qs

class StudyGroupSelect2Widget(s2forms.ModelSelect2Widget):
    model = StudyGroup
    search_fields = ["name__icontains"]


class UserSelect2SingleWidget(s2forms.ModelSelect2MultipleWidget):
    model = User
    search_fields = [
        "username__icontains",
        "first_name__icontains",
        "last_name__icontains",
    ]

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        dependent_fields.pop("course_id", None)
        return super().filter_queryset(request, term, queryset=queryset, **dependent_fields)

    def get_queryset(self):
        return (
            User.objects.annotate(
                is_cyrillic=Case(
                    When(first_name__regex=r"^[А-ЯЁа-яё]", then=Value(0)),
                    default=Value(1),
                    output_field=IntegerField(),
                )
            ).order_by("is_cyrillic", "first_name", "last_name", "username")
        )

    def label_from_instance(self, obj):
        full_name = obj.get_full_name()
        return f"{full_name} (@{obj.username})" if full_name else obj.username

    def filter_queryset(self, request, term, queryset=None, **dependent_fields):
        if queryset is None:
            queryset = self.get_queryset()

        course_id = dependent_fields.get("course_id")
        if course_id:
            from .models import Course
            try:
                course = Course.objects.get(pk=course_id)
                queryset = queryset.exclude(id__in=course.students.values_list("id", flat=True))
            except Course.DoesNotExist:
                pass

        terms = [word for word in term.strip().split() if word]
        for word in terms:
            queryset = queryset.filter(
                Q(first_name__icontains=word)
                | Q(last_name__icontains=word)
                | Q(username__icontains=word)
                | Q(email__icontains=word)
            )
        return queryset


class AddStudentsToCourseForm(forms.Form):
    course_id = forms.IntegerField(widget=forms.HiddenInput(), required=False)
    students = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=UserSelect2MultipleWidget(
            attrs={
                "data-placeholder": "Выберите студентов...",
                "data-minimum-input-length": 0,
                "data-dropdown-parent": "#modal-students-course",
                "data-width": "100%",
                "class": "form-control django-select2",
                "style": "width: 100%;",
            },
            dependent_fields={"course_id": "course_id"},
        ),
        label="Студенты",
        required=True,
    )

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        if course:
            self.fields["course_id"].initial = course.pk
            self.fields["students"].queryset = User.objects.exclude(
                id__in=course.students.values_list("id", flat=True)
            )

class CourseModalForm(forms.ModelForm):
    """Форма создания/редактирования курса в модалке"""
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        widget=SubjectSelect2Widget(attrs=general_select2_attrs),
        label="Тема",
        required=True,
    )

    class Meta:
        model = Course
        fields = ["subject", "title", "overview", "is_public", "is_active"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название курса"}),
            "overview": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Краткое описание"}),
        }

    def save(self, commit=True):
        return super().save(commit=commit)


class CourseModuleInlineForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "description"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Название модуля"}),
            "description": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Описание"}),
        }


CourseModuleFormSet = forms.inlineformset_factory(
    Course,
    Module,
    form=CourseModuleInlineForm,
    extra=0,
    can_delete=True,
)
ModuleFormSet = CourseModuleFormSet

class CourseAssignGroupForm(forms.Form):
    group = forms.ModelChoiceField(
        label="Учебная группа",
        queryset=StudyGroup.objects.all(),
        required=True,
        widget=StudyGroupSelect2Widget(
            attrs={
                "data-placeholder": "Выберите группу...",
                "data-minimum-input-length": 0,
                "data-close-on-select": "true",
                "data-allow-clear": "true",
                "data-language": "ru",
                "data-width": "100%",
                "class": "form-control",
                "style": "width: 100%;",
            }
        ),
    )
    activated_at = forms.DateTimeField(
        label="Дата активации",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )
    due_date = forms.DateTimeField(
        label="Срок прохождения",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )
    notes = forms.CharField(
        label="Примечание",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Необязательно"}),
    )

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.course = course
        if course:
            active_group_ids = CourseGroupAssignment.objects.filter(
                course=course,
                is_active=True,
            ).values_list("group_id", flat=True)

            self.fields["group"].queryset = StudyGroup.objects.exclude(
                id__in=active_group_ids
            ).order_by("name")

    def clean(self):
        cleaned_data = super().clean()
        activated_at = cleaned_data.get("activated_at")
        due_date = cleaned_data.get("due_date")
        if activated_at and due_date and due_date < activated_at:
            raise ValidationError("Срок прохождения не может быть раньше даты активации.")
        return cleaned_data


class CourseAssignUserForm(forms.Form):
    user = forms.ModelMultipleChoiceField(
        label="Студент / Пользователь",
        queryset=User.objects.filter(is_active=True),
        widget=UserSelect2SingleWidget(
            attrs={
                "data-placeholder": "Выберите студента...",
                "data-minimum-input-length": 0,
                "data-maximum-selection-length": 1,
                "data-dropdown-parent": "#modal-groups-course",
                "data-width": "100%",
                "class": "form-control django-select2",
                "style": "width: 100%;",
            }
        ),
    )
    activated_at = forms.DateTimeField(
        label="Дата активации",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )
    due_date = forms.DateTimeField(
        label="Срок прохождения",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )
    notes = forms.CharField(
        label="Примечание",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Необязательно"}),
    )

    def clean_user(self):
        users = self.cleaned_data.get("user")
        if not users:
            raise ValidationError("Выберите студента.")
        return users.first() if hasattr(users, "first") else users[0]

    def __init__(self, *args, course=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.course = course

    def clean(self):
        cleaned_data = super().clean()
        activated_at = cleaned_data.get("activated_at")
        due_date = cleaned_data.get("due_date")
        if activated_at and due_date and due_date < activated_at:
            raise ValidationError("Срок прохождения не может быть раньше даты активации.")
        return cleaned_data


class CourseAssignmentDatesForm(forms.Form):
    activated_at = forms.DateTimeField(
        label="Дата активации",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )
    due_date = forms.DateTimeField(
        label="Срок прохождения",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "class": "form-control form-control-sm"}),
    )

    def clean(self):
        cleaned_data = super().clean()
        activated_at = cleaned_data.get("activated_at")
        due_date = cleaned_data.get("due_date")
        if activated_at and due_date and due_date < activated_at:
            raise ValidationError("Срок прохождения не может быть раньше даты активации.")
        return cleaned_data
class StudyGroupForm(forms.ModelForm):
    users = forms.ModelMultipleChoiceField(
        label="Студенты группы",
        queryset=User.objects.filter(is_active=True),
        required=False,
        widget=UserSelect2MultipleWidget(
            attrs={
                "data-placeholder": "Выберите студентов для добавления...",
                "data-minimum-input-length": 0,
                "data-dropdown-parent": "#modal-group-form",
                "data-width": "100%",
                "class": "form-control django-select2",
                "style": "width: 100%;",
            }
        ),
    )
    def clean_name(self):
        name = self.cleaned_data.get("name", "").strip()
        qs = StudyGroup.objects.filter(name__iexact=name)
        if self.instance and self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Группа с таким названием уже существует.")
        return name

    class Meta:
        model = StudyGroup
        fields = ["name", "description", "users"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Например: ИС-21"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Краткое описание группы..."}),
        }