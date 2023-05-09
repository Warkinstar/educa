from django.urls import path
from . import views

app_name = "chat"

urlpatterns = [
    path("room/<int:course_id>/", views.ChatMessageListView.as_view(), name="course_chat_room"),
    path("room/<int:course_id>/message/<message_pk>/delete", views.message_delete, name="message_delete"),
]
