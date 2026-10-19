from django import forms
from django_select2 import forms as s2forms
from unidecode import unidecode
from django.utils.text import slugify
from .models import Course, Subject, Module

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
    """Форма для добавления новой темы через Offcanvas"""
    class Meta:
        model = Subject
        fields = ["title"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название новой темы"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(unidecode(instance.title))
            slug = base_slug
            counter = 1
            while Subject.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


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
        fields = ["subject", "title", "overview"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "placeholder": "Название курса"}),
            "overview": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Краткое описание"}),
        }

    def save(self, commit=True):
        instance = super().save(commit=False)
        if not instance.slug:
            base_slug = slugify(unidecode(instance.title))
            slug = base_slug
            counter = 1
            while Course.objects.filter(slug=slug).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


class CourseModuleInlineForm(forms.ModelForm):
    class Meta:
        model = Module
        fields = ["title", "description", "module_price"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Название модуля"}),
            "description": forms.TextInput(attrs={"class": "form-control form-control-sm", "placeholder": "Описание"}),
            "module_price": forms.NumberInput(attrs={"class": "form-control form-control-sm", "step": "0.01", "placeholder": "0.00"}),
        }


CourseModuleFormSet = forms.inlineformset_factory(
    Course,
    Module,
    form=CourseModuleInlineForm,
    extra=0,
    can_delete=True,
)
ModuleFormSet = CourseModuleFormSet