from django.urls import re_path
from . import consumers  # consumers.py мы создадим следующим шагом

websocket_urlpatterns = [
    re_path(r'ws/notifications/(?P<user_id>\w+)/$', consumers.NotificationConsumer.as_asgi()),
]
