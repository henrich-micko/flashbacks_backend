from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from chat.serializers import MessageSerializer, MessageWritableSerializer
from chat.models import Message
from chat.permissions import IsEventMember
from chat.pagination import MessageCursorPagination


class MessageViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsEventMember]
    lookup_field = "pk"
    pagination_class = MessageCursorPagination

    def get_serializer_class(self):
        if self.action == "create":
            return MessageWritableSerializer
        return MessageSerializer

    def get_queryset(self):
        return Message.objects.filter(
            event_id=self.kwargs.get("event_id")
        )

    def perform_create(self, serializer):
        serializer.save(user=self.request.user, event_id=self.kwargs.get("event_id"))
