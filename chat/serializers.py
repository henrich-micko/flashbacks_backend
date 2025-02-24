from rest_framework import serializers
from chat.models import Message
from user.serializers import MiniUserSerializer
from user.serializers_fields import AnonymousOrMiniSerializerField
from event.models import Event


class MessageParentSerializer(serializers.ModelSerializer):
    user = AnonymousOrMiniSerializerField()

    class Meta:
        model = Message
        fields = [
            "pk",
            "content",
            "user",
        ]


class MessageSerializer(serializers.ModelSerializer):
    user = AnonymousOrMiniSerializerField()
    parent = MessageParentSerializer(read_only=True)
    liked_by = serializers.SerializerMethodField(read_only=True)
    event = serializers.PrimaryKeyRelatedField(
        queryset=Event.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Message
        fields = read_only_fields = [
            "pk",
            "user",
            "event",
            "content",
            "timestamp",
            "parent",
            "liked_by",
        ]

    def get_liked_by(self, obj: Message):
        if type(obj) is not Message:
            return []
        return [
            MiniUserSerializer(lb.user).data for lb in obj.likedmessage_set.all()
        ]


class MessageWritableSerializer(MessageSerializer):
    parent = serializers.PrimaryKeyRelatedField(
        queryset=Message.objects.all(),
        required=False,
        allow_null=True
    )

    content = serializers.CharField()

