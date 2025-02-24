from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import action, api_view
from rest_framework.authtoken.models import Token

from user.serializers import (CreateUserSerializer,
                              UserContextualSerializer,
                              MiniUserSerializer,
                              MiniUserContextualSerializer,
                              UpdateProfilePicture,
                              AuthMiniUserSerializer,
                              UpdateUserSerializer)

from user.models import User
from user.utils import validate_google_token, get_username_from_email
from user.notifications import get_notifications_data_for_user, notifications_exists
from friendship.models import Friendship, FriendRequest
from friendship.serializers import FriendRequestSerializer
from utils.mixins import SearchAPIMixin
from event.serializers import EventViewerSerializer
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from user.tasks import check_nsfw_user_profile_picture


@api_view(["POST"])
def google_auth(request):
    token = request.data.get("auth_token", None)
    if token is None:
        return Response(data={"auth_token": "Not provided."}, status=status.HTTP_400_BAD_REQUEST)

    is_token_valid, user_data = validate_google_token(token)
    if not is_token_valid:
        return Response(data={"auth_token": "Invalid token."}, status=status.HTTP_400_BAD_REQUEST)

    user, created = User.objects.get_or_create(
        email=user_data["email"],
        defaults={"username": get_username_from_email(user_data["email"])}
    )

    if created:
        user.is_active = True
        user.save()

    token, created = Token.objects.get_or_create(user=user)
    data = {"token": token.key, "created": created}
    return Response(data, status=status.HTTP_201_CREATED)


class AuthUserViewSet(viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @action(detail=False, methods=["get"])
    def me(self, request):
        serializer = AuthMiniUserSerializer(instance=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def me_complex(self, request):
        serializer = AuthMiniUserSerializer(instance=request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def requests(self, request):
        instance = FriendRequest.objects.filter(to_user=self.request.user)
        serializer = FriendRequestSerializer(instance=instance, many=True)
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def friends(self, request):
        instance = request.user.friends
        serializer = UserContextualSerializer(instance=instance, many=True, context={"request": request})
        return Response(data=serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def notifications(self, request):
        data = get_notifications_data_for_user(self.request.user)
        return Response(data=data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def notifications_exists(self, request):
        exists = notifications_exists(request.user)
        return Response(data={"exists": exists}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["post"])
    def update_profile_picture(self, request):
        serializer = UpdateProfilePicture(data=request.data, instance=request.user)
        if serializer.is_valid():
            serializer.save()
            check_nsfw_user_profile_picture.delay(user_id=self.request.user.id)
            return Response(data=MiniUserSerializer(instance=request.user).data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["patch"])
    def update_profile(self, request):
        serializer = UpdateUserSerializer(data=request.data, instance=request.user)
        if serializer.is_valid():
            serializer.save()
            return Response(data=MiniUserSerializer(instance=request.user).data, status=status.HTTP_200_OK)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserViewSet(SearchAPIMixin, viewsets.ModelViewSet):
    search_fields = ["username"]

    def get_queryset(self):
        return User.objects.all().exclude(pk=self.request.user.pk)

    def get_serializer_class(self):
        if self.action == "create": return CreateUserSerializer
        if self.action == "requests": return FriendRequestSerializer
        if self.action == "search": return MiniUserContextualSerializer
        if self.action == "viewers": return EventViewerSerializer
        return UserContextualSerializer

    def get_serializer(self, *args, **kwargs):
        if self.get_serializer_class().__name__ == "UserPOVSerializer":
            kwargs["user_pov"] = self.request.user
        return super().get_serializer(*args, **kwargs)

    def get_permissions(self):
        if self.action == "create":
            return [AllowAny()]
        return [IsAuthenticated()]

    def perform_create(self, serializer):
        instance = serializer.save()
        instance.set_password(serializer.data["password"])
        instance.is_active = True
        instance.save()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        response.data["token"] = Token.objects.get(user_id=response.data["id"]).key
        if response.data.get("password", None):
            del response.data["password"]
        return response

    @action(detail=True, methods=["get", "post", "put", "delete"])  # TODO: turn this into its own viewset
    def friendship(self, request, pk):
        auth_user: User = request.user
        instance: User = self.get_object()

        if request.method == "GET":
            serializer = self.get_serializer(instance=request.user.friends, many=True)
            return Response(data=serializer.data, status=status.HTTP_200_OK)

        if auth_user == instance:
            return Response(data={"detail": "You cannot do friends operation on yourself."},
                            status=status.HTTP_400_BAD_REQUEST)

        #  create friend request
        if request.method == "POST":
            if not auth_user.is_friend_with(instance):
                FriendRequest.objects.get_or_create(from_user=auth_user, to_user=instance)

        #  accept friend request
        elif request.method == "PUT":
            if not auth_user.is_friend_with(instance):
                friend_request = FriendRequest.objects.filter(from_user=instance, to_user=auth_user).first()
                if friend_request is not None:
                    friend_request.status = FriendRequest.StatusChoices.ACCEPTED
                    friend_request.save()

        #  delete friendship or friend request
        elif request.method == "DELETE":
            friendship = Friendship.objects.get(user_a=auth_user, user_b=instance)
            if friendship is not None: friendship.delete()
            else:
                friend_request = FriendRequest.objects.get(user_a=auth_user, user_b=instance)
                friend_request.status = FriendRequest.StatusChoices.REFUSED
                friend_request.save()

        serializer = self.get_serializer(instance=instance)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def viewers(self, request, pk):
        instance = self.get_object()

        if not request.user.is_friend_with(instance):
            return Response(
                data={"detail": "You cannot see the viewers of not your friend."},
                status=status.HTTP_400_BAD_REQUEST
            )

        queryset = instance.viewers_for_user(for_user=request.user)
        serializer = self.get_serializer(instance=queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
