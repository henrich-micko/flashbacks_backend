# routing.py
from django.urls import re_path
from chat.consumers import ChatConsumer

# Define WebSocket URL pattern with dynamic event_id
websocket_urlpatterns = [
    re_path(r'ws', ChatConsumer.as_asgi()),  # event_id will be captured here
]
