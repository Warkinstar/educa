from django.forms import inlineformset_factory
from .models import Course, Module
from django.forms import forms


ModuleFormSet = inlineformset_factory(
    Course,
    Module,
    fields=["title", "description"],
    extra=2,
    can_delete=True,
)
