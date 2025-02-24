from django.db.models import signals
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from user.models import User


@receiver(signals.post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
