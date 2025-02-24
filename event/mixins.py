from event.serializers import EventSerializer
from event.models import Event


class EventMixin:
    lookup_field = "pk"
    serializer_class = EventSerializer
    queryset = Event.objects.all()
