from rest_framework import serializers
from event import models, validators
from user.serializers import UserSerializer, MiniUserSerializer
from utils.time import humanize_event_time


class MiniEventSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Event
        fields = [
            "pk",
            "title",
            "start_at",
            "end_at",
            "emoji"
        ]


class EventSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    quick_detail = serializers.SerializerMethodField()
    flashbacks_count = serializers.SerializerMethodField()

    class Meta:
        model = models.Event
        fields = [
            "pk",
            "title",
            "start_at",
            "end_at",
            "quick_detail",
            "status",
            "emoji",
            "viewers_mode",
            "mutual_friends_limit",
            "flashbacks_count",
            "allow_nsfw"
        ]
        ordering = ["start_at", "pk"]

    def validate(self, attrs):
        start_at, end_at = attrs.get("start_at"), attrs.get("end_at")
        if start_at and end_at:
            validators.validate_event_datetimes(start_at, end_at)
        return attrs

    def get_quick_detail(self, obj: models.Event) -> str:
        return humanize_event_time(obj.start_at)

    def get_status(self, obj: models.Event) -> int:
        return obj.status.value

    def get_flashbacks_count(self, obj):
        return obj.flashbacks.count()


"""Viewer Serializers"""


class EventPreviewFlashbackSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.Flashback
        fields = [
            "pk",
            "media"
        ]


class EventPreviewSerializer(serializers.ModelSerializer):
    flashback = EventPreviewFlashbackSerializer()

    class Meta:
        model = models.EventPreview
        fields = [
            "pk",
            "flashback",
            "order"
        ]


class EventViewerSerializer(serializers.ModelSerializer):
    event = EventSerializer(read_only=True)
    flashbacks_count = serializers.SerializerMethodField()
    preview = serializers.SerializerMethodField()
    is_host = serializers.SerializerMethodField()

    class Meta:
        model = models.EventViewer
        fields = [
            "pk",
            "event",
            "flashbacks_count",
            "preview",
            "is_member",
            "is_opened",
            "is_host"
        ]

    def get_flashbacks_count(self, obj):
        return obj.event.flashbacks.count()

    def get_preview(self, obj):
        return EventPreviewSerializer(
            instance=obj.event.eventpreview_set.all().order_by("order"),
            many=True
        ).data

    def get_is_host(self, obj):
        if not obj.is_member:
            return False
        em = models.EventMember.objects.filter(event=obj.event, user=obj.user).first()
        return True if em is not None and em.role == models.EventMemberRole.HOST else False

class EventMemberSerializer(serializers.ModelSerializer):
    user = MiniUserSerializer()
    added_by = MiniUserSerializer()

    class Meta:
        model = models.EventMember
        fields = [
            "pk",
            "user",
            "event",
            "role",
            "added_by"
        ]


class FlashbackSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()
    preview_order = serializers.SerializerMethodField()

    class Meta:
        model = models.Flashback
        fields = [
            "id",
            "media",
            "media_type",
            "video_media",
            "created_at",
            "created_by",
            "preview_order",
        ]

    def get_created_by(self, obj: models.Flashback):
        return MiniUserSerializer(instance=obj.event_member.user).data

    def get_preview_order(self, obj: models.Flashback):
        preview = obj.eventpreview_set.first()
        return preview.order if preview is not None else None

    def validate(self, data):
        media = data.get("media")
        video_media = data.get("video_media")

        if not media and not video_media:
            raise serializers.ValidationError("Either 'media' or 'video_media' must be provided.")

        return data


class FlashbackViewerSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.FlashbackViewer
        fields = [
            "id",
            "flashback",
            "is_seen",
        ]


class EventPosterTemplateColorPaletteSerializer(serializers.ModelSerializer):

    class Meta:
        model = models.EventPosterTemplateColorPalette
        fields = [
            "id",
            "color",
            "light_color"
        ]


class EventPosterTemplateSerializer(serializers.ModelSerializer):
    color_palettes = EventPosterTemplateColorPaletteSerializer(many=True)

    class Meta:
        model = models.EventPosterTemplate
        read_only_fields = fields = [
            "id",
            "title",
            "color_palettes"
        ]


class EventInviteSerializer(serializers.ModelSerializer):
    user = MiniUserSerializer()
    invited_by = MiniUserSerializer()

    class Meta:
        model = models.EventInvite
        read_only_fields = fields = [
            "id",
            "event",
            "user",
            "status",
            "invited_by"
        ]


