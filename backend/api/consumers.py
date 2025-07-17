import json
from channels.generic.websocket import AsyncWebsocketConsumer

from django.contrib.auth.models import User
from api.models import Profile

from asgiref.sync import sync_to_async


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f"user_{self.user_id}"

        # Подключаемся к группе (по user_id)
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Отключение от группы
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        # Можно использовать, если клиент что-то отправляет (необязательно для уведомлений)
        pass

    async def send_notification(self, event):
        # Получаем сообщение из события
        message = event['message']

        # Отправляем клиенту по WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

async def connect(self):
    self.user_id = self.scope['url_route']['kwargs']['user_id']
    self.group_name = f"user_{self.user_id}"

    # 🔒 Проверяем разрешено ли подключение к WebSocket
    try:
        user = await sync_to_async(User.objects.get)(id=self.user_id)
        profile = await sync_to_async(Profile.objects.get)(user=user)
        if not profile.notifications_enabled:
            await self.close()  # ⛔ Закрываем соединение
            return
    except Exception as e:
        print(f"[WebSocket ERROR] {e}")
        await self.close()
        return

    await self.channel_layer.group_add(self.group_name, self.channel_name)
    await self.accept()
