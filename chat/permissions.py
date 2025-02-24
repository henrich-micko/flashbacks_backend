from rest_framework.permissions import BasePermission
from event.models import EventMember


class IsEventMember(BasePermission):
    lookup_field = "event_id"

    def has_permission(self, request, view):
        print(request.user)
        event_id = view.kwargs.get(self.lookup_field, None)
        if event_id is None:
            return False
        try: EventMember.objects.get(event_id=event_id, user=view.request.user)
        except EventMember.DoesNotExist:
            return False
        return True
