from rest_framework import serializers

from friendship.models import FriendRequest, Friendship
from user.serializers import UserSerializer


class FriendRequestSerializer(serializers.ModelSerializer):
    to_user = UserSerializer()
    from_user = UserSerializer()

    class Meta:
        model = FriendRequest
        fields = [
            "id",
            "to_user",
            "from_user",
            "status",
            "date"
        ]


class FriendshipSerializer(serializers.ModelSerializer):
    with_user = serializers.SerializerMethodField()

    class Meta:
        model = Friendship
        fields = [
            "pk",
            "with_user",
            "date",
        ]

    def get_with_user(self, obj):
        other = obj.get_friend(self.context['request'].user)
        return None if not other else BasicUserSerializer(instance=other).data
