from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from user.serializers import UserSerializer, CreateUserSerializer
from user.models import User


class UserMixin:
    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "pk"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance=instance)
        return Response(serializer.data)


class CreateUserMixin:
    serializer_class = CreateUserSerializer
    queryset = User.objects.all()

    def perform_create(self, serializer):
        instance: User = serializer.save()
        instance.set_password(serializer.data["password"])
        instance.is_active = True
        instance.save()
        return instance
