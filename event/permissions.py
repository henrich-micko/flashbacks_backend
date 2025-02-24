from django.shortcuts import get_object_or_404
from rest_framework.permissions import BasePermission
from event.models import EventMember, EventMemberRole


class IsEventHost(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        try:
            event = EventMember.objects.get(event=obj, user=request.user)
            return event.role == EventMemberRole.HOST
        except EventMember.DoesNotExist:
            return False
