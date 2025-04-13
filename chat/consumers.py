import json, enum
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from asgiref.sync import sync_to_async
from django.conf import settings

from chat.serializers import MessageWritableSerializer, MessageSerializer
from chat.models import Message


"""
Message format:
{
    "type": <TYPE: MessageRequest/MessageResponse>,
    "data": <TYPE: dict>
}
"""


class MessageRequest(enum.Enum):
    message = 0
    like_unlike_message = 1


class MessageResponse(enum.Enum):
    message = 0
    notification = 1


class ChatConsumer(AsyncWebsocketConsumer):
    MESSAGE_TYPE_FIELD = "type"
    MESSAGE_DATA_FIELD = "data"

    event_group_name_format = "event_{event_id}_chat"
    notification_group_name = "notification"

    request_router = {
        MessageRequest.message.value: "handle_message",
        MessageRequest.like_unlike_message.value: "handle_like_unlike_message",
    }

    joined_groups: set

    """
    functions
    """

    @property
    def user(self):
        return self.scope.get("user", None)

    async def add_user_to_groups(self):
        for event in await self.get_user_events():
            event_group_name = self.event_group_name_format.format(event_id=event.id)
            try: await self.channel_layer.group_add(event_group_name, self.channel_name)
            except:
                print(f"Error: {event_group_name} group add failed.")
                continue
            self.joined_groups.add(event_group_name)

        await self.channel_layer.group_add("notification", self.channel_name)
        self.joined_groups.add("notification")

        user_group = f"user_{self.user.id}"
        await self.channel_layer.group_add(user_group, self.channel_name)
        self.joined_groups.add(user_group)

    async def remove_user_from_groups(self):
        for group in self.joined_groups.copy():
            await self.channel_layer.group_discard(group, self.channel_name)
            self.joined_groups.remove(group)

    def generate_chat_message(self, message_type, message_data):
        return {
            self.MESSAGE_TYPE_FIELD: "chat_message",
            self.MESSAGE_DATA_FIELD: {
                self.MESSAGE_TYPE_FIELD: message_type.value, self.MESSAGE_DATA_FIELD: message_data,
            }
        }

    @sync_to_async
    def get_user_events(self):
        return list(self.user.events)

    async def add_user_to_group(self, event):
        event_id = event.get("event_id", None)
        if event_id is None: return
        event_group_name = self.event_group_name_format.format(event_id=event_id)
        await self.channel_layer.group_add(event_group_name, self.channel_name)

        print("added to group", self.user)

    """
    request handler
    """

    async def handle_message(self, data):

        @sync_to_async
        def store_and_serializer_message():
            group_name = self.event_group_name_format

            serializer = MessageWritableSerializer(data=data)
            if serializer.is_valid():
                instance = serializer.save(user=self.user)
                group_name = group_name.format(event_id=instance.event.id)
                return group_name, MessageSerializer(instance=instance).data
            return group_name, None

        group_name, message_data = await store_and_serializer_message()
        if message_data is None: return

        await self.channel_layer.group_send(
            group_name,
            self.generate_chat_message(
                message_type=MessageResponse.message,
                message_data=message_data
            )
        )

    async def handle_like_unlike_message(self, data):
        try: message_id = int(data.get("id"))
        except (ValueError, TypeError): return None

        @sync_to_async
        def like_unlike_message():
            try: message = Message.objects.get(pk=message_id)
            except Message.DoesNotExist: return None, None

            group_name = self.event_group_name_format.format(event_id=message.event.id)
            if group_name not in self.joined_groups: return None, None

            instance, created = message.likedmessage_set.get_or_create(user=self.user)
            print(instance, created)
            if not created: instance.delete()
            return group_name, MessageSerializer(instance=message).data

        group_name, message_data = await like_unlike_message()
        if message_data is None: return

        await self.channel_layer.group_send(
            group_name,
            self.generate_chat_message(
                message_type=MessageResponse.message,
                message_data=message_data
            )
        )

    """
    convertor
    """

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["data"]))

    async def add_to_group(self, event):
        pass

    """
    on events
    """

    async def connect(self):
        if self.user == AnonymousUser():
            await self.close()
            return

        self.joined_groups = set()
        await self.add_user_to_groups()
        await self.accept()

    async def disconnect(self, close_code):
        await self.remove_user_from_groups()
        await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data)

        message_type, message_data = data.get(self.MESSAGE_TYPE_FIELD, None), data.get(self.MESSAGE_DATA_FIELD, None)
        if type(message_type) is not int or type(message_data) is not dict:
            return

        response_handler_name = self.request_router.get(message_type, None)
        if response_handler_name is None: return

        try: response_handler = self.__getattribute__(response_handler_name)
        except: return

        if not settings.DEBUG:
            try: await response_handler(message_data)
            except Exception as e:
                print(f"Error: {message_type} handler failed with error {e}.")
                return
        else: await response_handler(message_data)