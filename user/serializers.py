from rest_framework.serializers import ModelSerializer, SerializerMethodField

from user.models import User
from friendship.status import get_friendship_status


class CreateUserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password",
            "profile",
        ]

        read_only_fields = [
            "id",
            "profile"
        ]

class UpdateUserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "about",
        ]

        extra_kwargs = {
            "username": {"required": False},
            "about": {"required": False},
        }


class UserSerializer(ModelSerializer):
    quick_detail = SerializerMethodField()
    profile_url = SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "quick_detail",
            "profile_url"
        ]

    def get_quick_detail(self, obj: User) -> str:
        return "He is cool"

    def get_profile_url(self, obj: User) -> str:
        return "https://www.alexgrey.com/img/containers/art_images/Godself-2012-Alex-Grey-watermarked.jpeg/121e98270df193e56eeaebcff787023f.jpeg"


class UserPOVSerializer(UserSerializer):
    friendship_status = SerializerMethodField()

    class Meta(UserSerializer.Meta):
        fields = [
            *UserSerializer.Meta.fields,
            "friendship_status"
        ]

    def __init__(self, *args, **kwargs):
        self.user_pov = kwargs.pop("user_pov")
        super().__init__(*args, **kwargs)

    def get_friendship_status(self, obj):
        return get_friendship_status(
            user_from=self.user_pov,
            user_to=obj
        ).value


class MiniUserSerializer(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "profile",
            "about"
        ]


class MiniUserContextualSerializer(MiniUserSerializer):
    friendship_status = SerializerMethodField()
    mutual_friends = SerializerMethodField()

    class Meta(MiniUserSerializer.Meta):
        read_only_fields = fields = [
            *MiniUserSerializer.Meta.fields,
            "friendship_status",
            "mutual_friends",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.auth_user = self.context.get("request").user

    def get_friendship_status(self, obj):
        return get_friendship_status(user_from=self.auth_user, user_to=obj).value

    def get_mutual_friends(self, obj):
        return [
            MiniUserSerializer(instance=friend).data
            for friend in obj.mutual_friends(self.auth_user)
        ]


class UserContextualSerializer(MiniUserContextualSerializer):
    events_count = SerializerMethodField()
    friends_count = SerializerMethodField()
    flashbacks_count = SerializerMethodField()

    class Meta(MiniUserContextualSerializer.Meta):
        read_only_fields = fields = [
            *MiniUserContextualSerializer.Meta.fields,
            "events_count",
            "friends_count",
            "flashbacks_count"
        ]

    def get_events_count(self, obj: User):
        return obj.events.count()

    def get_friends_count(self, obj: User):
        return obj.friends.count()

    def get_flashbacks_count(self, obj: User):
        return obj.flashbacks.count()


class UpdateProfilePicture(ModelSerializer):

    class Meta:
        model = User
        fields = [
            "profile"
        ]


class AuthMiniUserSerializer(MiniUserSerializer):
    events_count = SerializerMethodField()
    friends_count = SerializerMethodField()
    flashbacks_count = SerializerMethodField()

    class Meta(MiniUserSerializer.Meta):
        read_only_fields = fields = [
            *MiniUserSerializer.Meta.fields,
            "events_count",
            "friends_count",
            "flashbacks_count",
            "date_joined",
        ]

    def get_events_count(self, obj: User):
        return obj.events.count()

    def get_friends_count(self, obj: User):
        return obj.friends.count()

    def get_flashbacks_count(self, obj: User):
        return obj.flashbacks.count()

