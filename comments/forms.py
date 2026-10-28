from django import forms
from django.contrib.auth import get_user_model

from comments.models import Comment


class CommentForm(forms.ModelForm):
    upload_session_id = forms.UUIDField(widget=forms.HiddenInput)

    notify_users = forms.ModelMultipleChoiceField(
        queryset=get_user_model().objects.filter(is_active=True),
        widget=forms.MultipleHiddenInput,
        required=False,
    )

    notify_reply_to = forms.BooleanField(
        required=False,
        label="Уведомить по почте отмеченного участника",
    )

    notify_participants = forms.BooleanField(
        required=False,
        label="Уведомить по почте участников",
    )

    class Meta:
        model = Comment
        fields = ["reply_to", "mention", "text", "notify_users"]
        widgets = {
            "reply_to": forms.HiddenInput,
            "mention": forms.HiddenInput,
            "text": forms.Textarea(
                attrs={
                    "class": "form-control form-control-sm",
                    "rows": 4,
                    "placeholder": "Введите текст комментария...",
                }
            ),
        }
        labels = {
            "text": "",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["reply_to"].widget.attrs.update({"x-model": "reply_to"})
        self.fields["mention"].widget.attrs.update({"x-model": "mention"})
        self.fields["notify_reply_to"].widget.attrs.update({"x-model": "notify_reply_to"})
        self.fields["notify_participants"].widget.attrs.update({"x-model": "notify_participants"})
        self.fields["notify_users"].widget.attrs.update({"x-model": "notify_users"})