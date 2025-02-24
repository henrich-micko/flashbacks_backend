from rest_framework import serializers
from user.serializers import MiniUserSerializer


class AnonymousOrMiniSerializerField(serializers.ReadOnlyField):
    def to_representation(self, value):
        if value is None:
            MiniUserSerializer.anonymous()
        serializer = MiniUserSerializer(value)
        return serializer.data
