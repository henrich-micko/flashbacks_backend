from django.db.models.signals import post_save
from django.dispatch import receiver
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from event.models import EventMember


@receiver(post_save, sender=EventMember)
def add_user_to_event_chat(sender, instance, created, **kwargs):
    if not created:
        return

    channel_layer = get_channel_layer()
    event_id = instance.event.id
    user_id = instance.user.id

    async_to_sync(channel_layer.group_add)(
        f"event_{event_id}",
        f"user_{user_id}"
    )