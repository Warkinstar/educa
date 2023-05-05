import json
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
from asgiref.sync import async_to_sync
from django.utils import timezone
from channels.db import database_sync_to_async
from courses.models import Course
from .models import Message


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.course_id = self.scope["url_route"]["kwargs"]["course_id"]
        self.room_group_name = f"chat_{self.course_id}"  # course id
        # join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        # accept connection, might to reject if demand
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Вызывается только у пользователя, который отправил сообщение"""
        text_data_json = json.loads(text_data)  # json in dict
        message = text_data_json["message"]  # exctract message
        now = timezone.now()
        # self.send(text_data=json.dumps({"message": message}))  # сообщение в канал
        await self.channel_layer.group_send(  # Сообщение в группу
            self.room_group_name,
            {
                "type": "chat_message",  # Invoke chat_message method *
                "message": message,
                "user": self.user.get_full_name(),
                "datetime": now.isoformat(),
            }
        )
        # save message in db
        course = await self.get_course(self.course_id)
        save_message = await self.save_message(course, self.user, message)
        # print(f"Сообщение '{self.save_message}' было сохранено.")

    @database_sync_to_async
    def get_course(self, pk):
        return Course.objects.get(pk=pk)

    @database_sync_to_async
    def save_message(self, course, user, content):
        Message.objects.create(course=course, user=user, content=content)

    async def chat_message(self, event):
        """Вызывается у всех пользователей включая, того кто отправил сообщение"""
        # send message to WebSocket and on page
        # print(f"Сообщение было принято: {self.user}")
        await self.send(text_data=json.dumps(event))  # Отправить себе
