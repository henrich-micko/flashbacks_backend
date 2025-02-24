from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from user.models import User


class FriendshipStatus(Enum):
    FRIENDS = 0
    REQUEST_TO_ME = 1
    REQUEST_FROM_ME = 2
    NONE = 3


def get_friendship_status(user_from: "User", user_to: "User") -> FriendshipStatus:
    from friendship.models import FriendRequest

    if user_from.is_friend_with(user_to): return FriendshipStatus.FRIENDS
    friend_request = FriendRequest.objects.get(user_a=user_from, user_b=user_to)
    if friend_request is None: return FriendshipStatus.NONE
    if friend_request.from_user == user_from: return FriendshipStatus.REQUEST_FROM_ME
    return FriendshipStatus.REQUEST_TO_ME
