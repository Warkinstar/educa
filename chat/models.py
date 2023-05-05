from django.db import models
from django.conf import settings
from courses.models import Course


class BaseModel(models.Model):
    """Base model with common fields"""

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Message(BaseModel):
    """Message in course chat room"""

    course = models.ForeignKey(Course, related_name="messages", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="messages", on_delete=models.CASCADE)
    content = models.TextField()

    class Meta:
        ordering = ["created"]
        indexes = [
            models.Index(fields=["created"]),
        ]

    def __str__(self):
        return f"Message by {self.user.get_full_name()} on '{self.course}'"
