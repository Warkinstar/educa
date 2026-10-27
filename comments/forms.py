from django import forms
from .models import Comment, CommentFile
from .validators import validate_comment_file


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class CommentForm(forms.ModelForm):
    files = MultipleFileField(
        required=False,
        label="Прикрепить файлы (до 10 МБ)"
    )

    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Напишите комментарий или вопрос...'
                }
            )
        }

    def clean_files(self):
        files = self.files.getlist('files')
        for f in files:
            validate_comment_file(f)
        return files