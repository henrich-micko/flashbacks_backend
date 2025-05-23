import uuid

from django.db.models import QuerySet
from django.shortcuts import get_object_or_404
from django.http import HttpResponse, FileResponse

from rest_framework import viewsets, permissions, status, mixins
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from celery import chain

from event import serializers as event_serializers
from event import models as event_models
from event.permissions import IsEventHost
from event.tasks import check_nsfw_flashbacks, process_flashback
from user.serializers import MiniUserSerializer, MiniUserContextualSerializer
from user.models import User
from utils.shortcuts import get_object_or_exception
from utils.mixins import SearchAPIMixin
from utils.views import parse_int_value, parse_str_value, parse_boolean_value
from event.status import EventMemberStatus

import boto3
from django.conf import settings


class EventViewSet(SearchAPIMixin, viewsets.ModelViewSet):
    lookup_field = "pk"
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    search_fields = ["title", "emoji"]

    def get_serializer_class(self):
        if self.action in ("to_view", "mark_as_open"): return event_serializers.EventViewerSerializer
        if self.action == "poster_templates": return event_serializers.EventPosterTemplateSerializer
        return event_serializers.EventSerializer

    def get_permissions(self):
        output = [permissions.IsAuthenticated()]
        if self.action in ["put", "patch"]:
            output.append(IsEventHost())
        return output

    def perform_create(self, serializer) -> None:
        instance = serializer.save()
        event_models.EventMember.objects.create(
            user=self.request.user,
            event=instance,
            role=event_models.EventMemberRole.HOST
        )

    def perform_update(self, serializer) -> None:
        instance: event_models.Event = serializer.save()
        if not instance.allow_nsfw:
            for preview in instance.eventpreview_set.all():
                if preview.flashback.is_nsfw:
                    preview.switch_flashback_random()

    def get_queryset(self) -> QuerySet:
        qs = self.request.user.events.order_by("-start_at")

        # filtering by status
        status_filter = self.request.query_params.get("status", None)
        if status_filter is not None:
            try: status_filter = int(status_filter)
            except ValueError: return qs
            qs = qs.filter_by_status(status=status_filter)
        return qs

    @action(detail=True, methods=["post"])
    def close(self, request, pk):
        event = get_object_or_404(self.get_queryset(), pk=pk)
        event.close()
        return Response(self.get_serializer(instance=event).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def to_view(self, request, **kwargs):
        ev = event_models.EventViewer.objects.filter(user=self.request.user).order_by("-event__end_at")
        search_query = request.query_params.get("q", None)
        is_member_filter = parse_boolean_value(request.query_params.get("is_member"), default=None)
        if is_member_filter is not None:
            ev = ev.filter(is_member=True)
        if search_query is not None:
            ev = ev.filter(event__title__icontains=search_query)
        return Response(self.get_serializer(ev, many=True).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_friends_members(self, request, pk):
        event = get_object_or_404(self.get_queryset(), pk=pk)
        members = event.get_friends_members(request.user)
        data = event_serializers.EventMemberSerializer(members, many=True).data
        return Response(data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def validate_dates(self, request, **kwargs):
        start_at = self.request.query_params.get("start_at", None)
        end_at = self.request.query_params.get("end_at", None)

        if start_at is None or end_at is None:
            return Response(status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def curr_event(self, request):
        instance = request.user.curr_event
        if instance is None:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(data=event_serializers.EventSerializer(instance=instance).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def mark_as_open(self, request, pk):
        event_viewer = get_object_or_exception(
            event_models.EventViewer.objects.all(), PermissionDenied(), event__pk=pk, user=self.request.user
        )

        event_viewer.is_opened = True
        event_viewer.save()

        return Response(self.get_serializer(event_viewer).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def poster_generate(self, request, pk):
        template_id = parse_int_value(request.query_params, "template")
        template = get_object_or_404(event_models.EventPosterTemplate, id=template_id)

        color_id = parse_int_value(request.query_params, key="color")
        color_palette = get_object_or_404(template.color_palettes, id=color_id)

        file_type = request.query_params.get("file_type", "html")
        event = self.get_object()

        if file_type == "html":
            return HttpResponse(
                template.render_html(event, color_palette),
                content_type="application/html"
            )
        if file_type == "pdf":
            response = HttpResponse(template.render_pdf(event, color_palette), content_type="application/pdf")
            response["Content-Disposition"] = f'inline; filename="{event.title}_poster.pdf"'
            return response
        return Response({"file_type": ["Invalid file type. (html/pdf)"]}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get"])
    def poster_templates(self, request, **kwargs):
        serializer = self.get_serializer(
            instance=event_models.EventPosterTemplate.objects.all(),
            many=True,
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def invite(self, request, **kwargs):
        invite_code_value = parse_str_value(request.query_params, "code")
        invite_code: event_models.EventInviteCode = get_object_or_404(
            event_models.EventInviteCode.objects.all(), code=invite_code_value
        )
        invite_code.add_member(request.user)
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def check_invite_code(self, request, **kwargs):
        invite_code_value = parse_str_value(request.query_params, "code")
        invite_code: event_models.EventInviteCode = get_object_or_404(
            event_models.EventInviteCode.objects.all(), code=invite_code_value
        )
        return Response(self.get_serializer(invite_code.event).data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_invite_code(self, request, **kwargs):
        invite, created = event_models.EventInviteCode.objects.get_or_create(event=self.get_object())
        return Response({"code": invite.code}, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def get_viewer(self, request, **kwargs):
        viewer = get_object_or_404(event_models.EventViewer.objects.all(), event=self.get_object(), user=self.request.user)
        return Response(
            event_serializers.EventViewerSerializer(instance=viewer).data,
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=["post"])
    def set_preview(self, request, **kwargs):
        for order in self.request.data.keys():
            if type(order) is not str and type(order) is not int:
                continue

            preview = get_object_or_404(event_models.EventPreview, order=order, event=self.get_object())
            flashback = get_object_or_404(event_models.Flashback, id=self.request.data[order])

            preview.flashback = flashback
            preview.save()
        return Response(status=status.HTTP_200_OK)


class EventFlashbackViewSet(mixins.ListModelMixin,
                            mixins.RetrieveModelMixin,
                            mixins.CreateModelMixin,
                            mixins.DestroyModelMixin,
                            viewsets.GenericViewSet):

    lookup_field = "pk"
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    serializer_class = event_serializers.FlashbackSerializer

    def get_queryset(self):
        event_viewer = get_object_or_exception(
            event_models.EventViewer.objects.all(), PermissionDenied(),
            event__pk=self.kwargs.get("event_id"),
            user__pk=self.request.user.pk
        )

        queryset = event_models.Flashback.objects.filter(
            event_member__event__pk=event_viewer.event.pk
        )

        if not event_viewer.event.allow_nsfw:
            nsfw_flashbacks = [i.id for i in queryset.filter(is_nsfw=True)]
            queryset = queryset.exclude(id__in=nsfw_flashbacks)

        return queryset.order_by("created_at")

    def perform_create(self, serializer):
        event_member = get_object_or_exception(
            event_models.EventMember.objects.all(), PermissionDenied(),
            event__pk=self.kwargs.get("event_id", None),
            user=self.request.user
        )

        return serializer.save(event_member=event_member)

    def create(self, request, *args, **kwargs):
        event_member = get_object_or_exception(
            event_models.EventMember.objects.all(), PermissionDenied(),
            event__pk=self.kwargs.get("event_id", None),
            user=self.request.user
        )

        if event_member.event.status != event_models.EventStatus.ACTIVATED:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        serializer = event_serializers.CreateFlashbackSerializer(data=request.data)
        if serializer.is_valid():
            event_models.Flashback.objects.create(
                media=serializer.validated_data.get("media", None),
                video_media=serializer.validated_data.get("video_media", None),
                media_type=serializer.validated_data["media_type"],
                event_member=event_member,
            )

            return Response(status=status.HTTP_201_CREATED)
        return Response(data=serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["post"])
    def mark_as_seen(self, request, pk):
        flashback_viewer = get_object_or_exception(
            event_models.FlashbackViewer.objects.all(), PermissionDenied(), user=self.request.user, pk=pk
        )

        flashback_viewer.is_seen = True
        flashback_viewer.save()

    @action(detail=False, methods=["get"])
    def generate_storage(self, request, **kwargs):
        media_type = parse_int_value(self.request.query_params, "mt")
        if media_type == event_models.FlashbackMediaType.PHOTO.value:
            content_type, file_extension = "image/jpeg", "jpg"
        else:
            content_type, file_extension = "video/mp4", "mp4"
        file_path = f"media/private/flashback/{uuid.uuid4()}.{file_extension}"

        s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_DEFAULT_REGION
        )

        storage = s3_client.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': settings.AWS_STORAGE_BUCKET_NAME,
                'Key': file_path,
                "ContentType": content_type,
            },
            ExpiresIn=3600
        )

        return Response({"storage": storage, "path": file_path}, status=status.HTTP_200_OK)


class MemberViewSet(mixins.ListModelMixin,
                    mixins.RetrieveModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):

    lookup_field = "user__pk"
    serializer_class = event_serializers.EventMemberSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self) -> QuerySet:
        event_id = self.kwargs.get("event_id", None)
        event = get_object_or_404(event_models.Event.objects.all(), pk=event_id)

        is_member = event_models.EventMember.objects.filter(event=event, user=self.request.user).exists()
        is_invited = event_models.EventInvite.objects.filter(event=event, user=self.request.user).exists()

        if not is_member and not is_invited:
            raise PermissionDenied()

        return event_models.EventMember.objects.filter(event=event)

    @action(detail=False, methods=["get"])
    def invite(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        user_id = parse_int_value(self.request.query_params, "user")

        instance, created = event_models.EventInvite.objects.get_or_create(
            event_id=event_id, user_id=user_id, invited_by=self.request.user
        )

        if not created:
            instance.status == event_models.EventInviteStatus.PENDING
            instance.save()

        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def accept_invite(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        invite = get_object_or_404(event_models.EventInvite.objects.all(), event_id=event_id, user=self.request.user)
        invite.status = event_models.EventInviteStatus.ACCEPT
        invite.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def decline_invite(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        invite = get_object_or_404(event_models.EventInvite.objects.all(), event_id=event_id, user=self.request.user)
        invite.status = event_models.EventInviteStatus.DECLINE
        invite.save()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def delete_invite(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        user_id = parse_int_value(self.request.query_params, "user")
        event_models.EventInvite.objects.filter(event_id=event_id, user_id=user_id).delete()
        return Response(status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def invites(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        status_filter = parse_int_value(self.kwargs, "status", default=None)

        event_invites = event_models.EventInvite.objects.filter(event_id=event_id)
        if status_filter is not None:
            event_invites = event_invites.filter(status=status_filter)

        serializer = event_serializers.EventInviteSerializer(
            instance=event_invites, many=True
        )

        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def possible(self, request, *args, **kwargs):
        event_id = parse_int_value(self.kwargs, "event_id")
        search_filter = request.query_params.get("search", None)
        search_filter = search_filter.lower() if search_filter is not None else search_filter

        possible_members, members_id = set(), []
        for em in event_models.EventMember.objects.filter(event_id=event_id):
            members_id.append(em.user.id)
            for f in em.user.friends:
                if search_filter is not None and search_filter not in f.username.lower():
                    continue
                possible_members.add(f.id)

        response_data = []
        for pm_id in possible_members:
            if self.request.user.id == pm_id:
                continue
            data = MiniUserSerializer(instance=User.objects.get(id=pm_id)).data
            data["status"] = EventMemberStatus.NONE.value
            if pm_id in members_id:
                data["status"] = EventMemberStatus.MEMBER.value
            elif event_models.EventInvite.objects.filter(event_id=event_id, user_id=pm_id).exists():
                data["status"] = EventMemberStatus.INVITED.value
            response_data.append(data)
        return Response(response_data, status=status.HTTP_200_OK)
