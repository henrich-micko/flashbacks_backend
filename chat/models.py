from django.db import models

from event.models import Event
from user.models import User


class Message(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    parent = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, default=None, related_name="replies", blank=True)

    def __str__(self):
        return f"{self.user} to {self.event}"

    def like(self, user):
        LikedMessage.objects.get_or_create(user=user, message=self)

    def unlike(self, user):
        LikedMessage.objects.filter(user=user, message=self).delete()


class LikedMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.ForeignKey(Message, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "message")

    def __str__(self):
        return f"{self.user} liked {self.message}"
