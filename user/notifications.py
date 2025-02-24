from enum import Enum

from user.serializers import MiniUserSerializer
from event.serializers import MiniEventSerializer
from event.models import EventInvite


class NotificationType(Enum):
    friend_request = 0
    event_invitation = 1


class Notification:
    TYPE_FIELD = "type"
    DATA_FIELD = "data"

    type: NotificationType

    def to_json(self):
        return {
            self.TYPE_FIELD: self.type.value,
            self.DATA_FIELD: {},
        }


class FriendRequestNotification(Notification):
    type = NotificationType.friend_request
    user_serializer = MiniUserSerializer

    def __init__(self, from_user):
        self.from_user = from_user

    def to_json(self):
        response = super().to_json()
        response[self.DATA_FIELD] = {
            "from_user": self.user_serializer(self.from_user).data,
        }
        return response


class EventInvitationNotification(Notification):
    type = NotificationType.event_invitation
    user_serializer = MiniUserSerializer
    event_serializer = MiniEventSerializer

    def __init__(self, event_invite: EventInvite):
        self.event_invite = event_invite

    def to_json(self):
        response = super().to_json()
        response[self.DATA_FIELD] = {
            "invited_by": self.user_serializer(self.event_invite.invited_by).data,
            "event": self.event_serializer(self.event_invite.event).data,
        }
        return response

from friendship.models import FriendRequest


def get_notifications_data_for_user(user):
    notifications = []
    friend_requests = FriendRequest.objects.filter(to_user=user).order_by("-date")
    for fr in friend_requests:
        notifications.append(FriendRequestNotification(fr.from_user).to_json())
    event_invites = EventInvite.objects.filter(user=user).order_by("-date")
    for ei in event_invites:
        notifications.append(EventInvitationNotification(ei).to_json())
    return notifications


def notifications_exists(user) -> bool:
    from friendship.models import FriendRequest
    friend_requests = FriendRequest.objects.filter(to_user=user)
    event_invites = EventInvite.objects.filter(user=user)
    print(friend_requests.exists() or event_invites.exists())
    return friend_requests.exists() or event_invites.exists()
