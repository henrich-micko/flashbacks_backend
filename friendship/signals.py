from django.db.models.signals import post_save
from django.dispatch import receiver

from friendship.models import FriendRequest


@receiver(post_save, sender=FriendRequest)
def check_friend_request_status(sender, instance, **kwargs):
    instance.process()