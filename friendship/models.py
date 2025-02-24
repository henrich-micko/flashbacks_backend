from django.db import models
from django.utils import timezone

from user.models import User
from friendship.managers import FriendshipQuerySet, FriendRequestQuerySet


class Friendship(models.Model):
    objects = FriendshipQuerySet.as_manager()

    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendship_user_to")
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friendship_user_from")
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('to_user', 'from_user')

    def __str__(self):
        return f"{self.to_user} -> {self.from_user}"

    def get_friend(self, user_to_compare, default=None):
        if user_to_compare == self.from_user: return self.to_user
        if user_to_compare == self.to_user: return self.from_user
        return default


class FriendRequest(models.Model):
    objects = FriendRequestQuerySet.as_manager()

    class StatusChoices(models.IntegerChoices):
        PENDING = 0
        ACCEPTED = 1
        REFUSED = 2

    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_request_user_to")
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="friend_request_user_from")
    status = models.IntegerField(default=StatusChoices.PENDING, choices=StatusChoices.choices)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('to_user', 'from_user')

    def __str__(self):
        return f"{self.from_user} -> {self.to_user}"

    def process(self):
        if self.status == FriendRequest.StatusChoices.PENDING:
            return

        if self.status == FriendRequest.StatusChoices.ACCEPTED:
            return Friendship.objects.get_or_create(
                from_user=self.from_user,
                to_user=self.to_user
            ) and self.delete()

        self.delete()
