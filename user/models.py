import os.path
import uuid
import random

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.conf import settings

from user.manager import UserManager
from utils.nsfw_detection import check_nsfw_photo_aws


def upload_profile_to(instance, filename):
    extension = filename.split(".")[-1]
    return f"{settings.USER_PROFILE_FOLDER}/{uuid.uuid4()}.{extension}"

def default_profile_picture():
    return os.path.join(
        settings.USER_PROFILE_FOLDER,
        settings.DEFAULT_USER_PICTURE_FORMAT.format(
            id=random.randint(0, settings.DEFAULT_USER_PICTURE_COUNT - 1)
        )
    )

class User(AbstractBaseUser, PermissionsMixin):
    objects = UserManager()

    username = models.CharField(max_length=10, unique=True)
    email = models.EmailField(unique=True)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)
    profile = models.ImageField(
        upload_to=upload_profile_to,
        null=False,
        blank=False,
        default=default_profile_picture
    )
    about = models.CharField(max_length=25, default=None, null=True)

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS = ["email"]

    def __str__(self):
        return f"{self.pk}:{self.username}"

    @property
    def profile_key(self):
        return f"media/public/{self.profile}"

    @property
    def friendship_set(self):
        from friendship.models import Friendship
        return Friendship.objects.filter_by_user(self)

    def is_friend_with(self, user):
        from friendship.models import Friendship
        return Friendship.objects.get(user_a=self, user_b=user) is not None

    @property
    def events(self) -> models.QuerySet:
        from event.models import Event, EventMember

        return Event.objects.filter(
            pk__in=[em.event.pk for em in EventMember.objects.filter(user=self)]
        )

    @property
    def friends(self) -> models.QuerySet:
        from friendship.models import Friendship

        return User.objects.filter(
            id__in=[
                fs.get_friend(self).id for fs in self.friendship_set
            ]
        )

    def mutual_friends(self, other_user: "User") -> models.QuerySet:
        return self.friends.intersection(other_user.friends)

    @property
    def flashbacks(self):
        from event.models import Flashback
        return Flashback.objects.filter(event_member__user=self)

    def viewers_for_user(self, for_user):
        from event.models import EventViewer
        return EventViewer.objects.filter(user=for_user, event__in=self.events)

    @property
    def curr_event(self):
        curr_time = timezone.now()
        return self.events.filter(start_at__lte=curr_time, end_at__gte=curr_time).first()

    def check_nsfw_profile_picture(self):
        categories, is_nsfw = check_nsfw_photo_aws(self.profile_key)
        if is_nsfw:
            self.profile = default_profile_picture()
            self.save()
