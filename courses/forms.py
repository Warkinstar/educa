from django import forms
from .models import Course, Module


ModuleFormSet = forms.inlineformset_factory(
    Course,
    Module,
    fields=["title", "description"],
    extra=2,
    can_delete=True,
    widgets={"description": forms.Textarea(attrs={"rows": 3})},
)
