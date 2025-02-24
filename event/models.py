import uuid
import random
import segno
import io
import weasyprint
import base64
from enum import Enum

from django.db import models
from django.utils import timezone
from django.template.loader import render_to_string
from django.conf import settings

from event.managers import EventQuerySet, FlashbackQuerySet
from event.validators import hex_color_validator
from user.models import User
from utils.nsfw_detection import check_nsfw_google
from utils import colors


EVENT_PREVIEW_COUNT_MAX = 3


""" Enums and choices """

class EventStatus(Enum):
    OPENED = 0
    ACTIVATED = 1
    CLOSED = 2

class EventViewersMode(models.IntegerChoices):
    ONLY_MEMBERS = 0, "only_members"
    ALL_FRIENDS = 1, "all_friends"
    MUTUAL_FRIENDS = 2, "mutual_friends"

class FlashbackVisibilityMode(models.IntegerChoices):
    PUBLIC = 0, "public"
    PRIVATE = 1, "private"


class Event(models.Model):
    objects = EventQuerySet.as_manager()

    title = models.CharField(max_length=15)
    emoji = models.CharField(max_length=35)
    start_at = models.DateTimeField()
    end_at = models.DateTimeField()

    post_close_actions = models.BooleanField(default=False)

    # settings for event
    viewers_mode = models.IntegerField(
        default=EventViewersMode.ONLY_MEMBERS,
        choices=EventViewersMode.choices
    )
    mutual_friends_limit = models.DecimalField(
        max_digits=5, decimal_places=2, default=None, null=True)
    allow_nsfw = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.pk}:{self.title}"

    @property
    def status(self) -> EventStatus:
        current_time = timezone.now()
        if current_time < self.start_at: return EventStatus.OPENED
        if current_time > self.end_at: return EventStatus.CLOSED
        return EventStatus.ACTIVATED

    @property
    def host(self):
        return self.eventmember_set.filter(role=EventMemberRole.HOST).first()

    @property
    def viewers_generated(self) -> bool:
        return EventViewer.objects.filter(event=self).exists()

    def is_member(self, user: User) -> bool:
        try: EventMember.objects.get(event=self, user=user)
        except EventMember.DoesNotExist: return False
        return True

    def add_member_from_invite_code(self, user: "User", invite_code: "EventInviteCode"):
        return EventMember.objects.get_or_create(
            event=self, user=user, role=EventMemberRole.GUEST, added_by=self.host
        )

    def add_member_from_invite(self, event_invite: "EventInvite"):
        return EventMember.objects.get_or_create(
            event=self, user=event_invite.user, role=EventMemberRole.GUEST, added_by=event_invite.invited_by
        )

    def close(self):
        self.end_at = timezone.now()
        self.save()
        self.on_close()

    def on_close(self):
        self.generate_viewers()
        self.generate_preview()

    @property
    def flashbacks(self):
        return Flashback.objects.filter(
            event_member_id__in=(ev.id for ev in EventMember.objects.filter(event=self))
        )

    @property
    def invite_code(self):
        instance, _ = EventInviteCode.objects.get_or_create(event=self)
        return instance

    def get_friends_members(self, user: User) -> models.QuerySet["EventMember"]:
        return self.eventmember_set.filter(
            user__in=[u.get_friend(user).pk for u in user.friendship_set.all()]
        )

    def save(self, *args, **kwargs):
        if self.viewers_mode == EventViewersMode.MUTUAL_FRIENDS.value:
            if self.mutual_friends_limit is None:
                self.mutual_friends_limit = 0.3
        super().save(*args, **kwargs)

    def generate_preview(self):
        flashbacks = self.flashbacks.all()
        if self.viewers_mode != EventViewersMode.ONLY_MEMBERS:
            flashbacks = flashbacks.filter(visibility=FlashbackVisibilityMode.PUBLIC)

        # check the old ones
        for i, ep in enumerate(self.eventpreview_set.order_by("order")):
            if i + 1 >= EVENT_PREVIEW_COUNT_MAX or ep.flashback not in flashbacks:
                ep.delete()
            flashbacks = flashbacks.exclude(pk=ep.flashback.pk)
            ep.order = i + 1
            ep.save()

        # create the new ones
        ep_count = self.eventpreview_set.count()
        for i in range(EVENT_PREVIEW_COUNT_MAX - ep_count):
            if flashbacks.count() == 0:
                break
            random_flashback = random.choice(flashbacks)
            flashbacks = flashbacks.exclude(pk=random_flashback.pk)
            EventPreview.objects.create(event=self, flashback=random_flashback, order=i + 1 + ep_count)

    def generate_viewers(self):
        self._flush_viewers()
        self._generate_all_members_viewers()  # members should be always viewers

        if (self.viewers_mode == EventViewersMode.ALL_FRIENDS.value or
           (self.viewers_mode == EventViewersMode.MUTUAL_FRIENDS.value and self.mutual_friends_limit >= 1)):
            self._generate_all_friends_viewers()  # mode is ALL_FRIENDS or MUTUAL_FRIENDS with mfl over 1

        elif self.viewers_mode == EventViewersMode.MUTUAL_FRIENDS.value:
            self._generate_mutual_members_viewers()  # MUTUAL_FRIENDS

    def _generate_all_members_viewers(self):
        for em in self.eventmember_set.all():
            EventViewer.objects.get_or_create(
                user=em.user, event=self, is_member=True
            )

    def _generate_all_friends_viewers(self):
        for em in self.eventmember_set.all():
            for f in em.user.friends:
                EventViewer.objects.get_or_create(
                    user=f, event=self, is_member=False
                )

    def _generate_mutual_members_viewers(self):
        members_count = len(self.eventmember_set)
        mutual_friends_limit_c = round(members_count * ((self.mutual_friends_limit * 10) / 100))
        user_friends_count = {}
        for em in self.eventmember_set.all():
            for f in em.user.friends:
                mfc = user_friends_count.get(f.pk, 0)
                if mfc is True: continue
                user_friends_count[f.pk] = mfc + 1
                if mfc >= mutual_friends_limit_c:
                    EventViewer.objects.get_or_create(user=f, event=self, is_member=False)
                    user_friends_count[f.pk] = True

    def _flush_viewers(self):
        EventViewer.objects.filter(event=self).delete()


class EventInviteStatus(models.IntegerChoices):
    PENDING = 0, "pending"
    ACCEPT = 1, "accept"
    DECLINE = 2, "decline"


class EventInvite(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    invited_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="invited")
    status = models.IntegerField(choices=EventInviteStatus.choices, default=EventInviteStatus.PENDING)
    date = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self):
        return f"[{self.user}] invited to [{self.event} by [{self.invited_by}]]"

    def process(self):
        if self.status == EventInviteStatus.PENDING:
            return
        if self.status == EventInviteStatus.ACCEPT:
            self.event.add_member_from_invite(self)
            self.delete()
        if self.status == EventInviteStatus.DECLINE:
            self.delete()

class EventMemberRole(models.IntegerChoices):
    HOST = 0, "host"
    GUEST = 1, "guest"


class EventMember(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.IntegerField(default=EventMemberRole.GUEST, choices=EventMemberRole.choices)
    added_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="added_by", default=None, null=True)

    class Meta:
        unique_together = ("event", "user")

    def __str__(self) -> str:
        return f"{self.user} -{self.role}-> {self.event}"


def upload_flashback_to(instance, filename):
    extension = filename.split(".")[-1]
    return f"flashback/{uuid.uuid4()}.{extension}"


class Flashback(models.Model):
    objects = FlashbackQuerySet.as_manager()

    event_member = models.ForeignKey(EventMember, on_delete=models.CASCADE)
    created_at = models.DateTimeField(default=timezone.now)
    media = models.ImageField(upload_to=upload_flashback_to, blank=True, null=True)
    visibility = models.IntegerField(default=FlashbackVisibilityMode.PUBLIC, choices=FlashbackVisibilityMode.choices)
    is_nsfw = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"{self.event_member} flashback [{self.id}]"

    @property
    def user(self) -> User:
        return self.event_member.user

    @property
    def event(self) -> Event:
        return self.event_member.event

    def check_nsfw(self):
        categories, self.is_nsfw = check_nsfw_google(self.media)
        self.save()


class EventPreview(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    flashback = models.ForeignKey(Flashback, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)  # 1, 2...EVENT_PREVIEW_COUNT

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["event", "order"],
                name="unique_event_preview_event_order"
            ),
        ]

    def __str__(self) -> str:
        return f"Preview for event ({self.event}) with flashback ({self.flashback}) as {self.order}"

    def switch_flashback_random(self):
        flashbacks = self.event.flashbacks.all()
        for preview in EventPreview.objects.filter(event=self.event).exclude(id=self.id):
            flashbacks.exclude(id=preview.flashback.id)
        if not flashbacks.exists():
            self.delete()

        self.flashback = random.choice(flashbacks)
        print(f"switching for {self.flashback}")
        self.save()


class EventViewer(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    is_member = models.BooleanField(default=False)
    is_opened = models.BooleanField(default=False)

    class Meta:
        unique_together = ("user", "event")

    def __str__(self):
        return f"user:[{self.user}] -> event:[{self.event}]"

    def generate_flashback_viewer(self):
        for user in self.event.eventmember_set.all():
            for flashback in user.flashback_set.all():
                fv, created = FlashbackViewer.objects.get_or_create(event_viewer=self, flashback=flashback)
                if not created and fv.is_seen:
                    fv.is_seen = False
                    fv.save()


class FlashbackViewer(models.Model):
    event_viewer = models.ForeignKey(EventViewer, on_delete=models.CASCADE)
    flashback = models.ForeignKey(Flashback, on_delete=models.CASCADE)
    is_seen = models.BooleanField(default=False)

    class Meta:
        unique_together = ("event_viewer", "flashback")

    def __str__(self):
        return f"[{self.event_viewer}] -> {self.flashback}"


def generate_event_qrcode_code():
    return uuid.uuid4().hex[:8]


class EventInviteCode(models.Model):
    code = models.CharField(default=generate_event_qrcode_code, max_length=8)
    event = models.OneToOneField(Event, on_delete=models.CASCADE)

    def __str__(self):
        return f"Event invite code for {self.event}"

    @property
    def link(self):
        return f"{settings.DOMAIN}/event/invite?code={self.code}"

    def generate_qrcode(self, front_color="#ffffff", background_color="#000000") -> str:
        qrcode = segno.make(self.link, mask=7)
        buffer = io.BytesIO()
        qrcode.save(buffer, kind='png', scale=7, dark=front_color, light=background_color, border=1)

        # Get the image data as base64 encoded string
        qr_code_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

        return f"data:image/png;base64,{qr_code_base64}"

    def add_member(self, user):
        self.event.add_member_from_invite_code(user, self)


class EventPosterTemplate(models.Model):
    title = models.CharField(max_length=10, unique=True)
    html_file = models.CharField(max_length=15)

    def __str__(self):
        return self.title

    def render_html(self, event, color_palette: "EventPosterTemplateColorPalette"):
        context = {
            "event": event,
            "palette": color_palette,
        }

        return render_to_string(
            f"event/poster/{self.html_file}", context=context,
        )

    def render_pdf(self, event, color_palette: "EventPosterTemplateColorPalette"):
        return weasyprint.HTML(string=self.render_html(event, color_palette)).write_pdf(
            stylesheets=[
                weasyprint.CSS(string='@page { size: A4; margin: 0; }')
            ]
        )


class EventPosterTemplateColorPalette(models.Model):
    template = models.ForeignKey(EventPosterTemplate, on_delete=models.CASCADE, related_name="color_palettes")
    color = models.CharField(max_length=9, validators=[hex_color_validator])
    light_color = models.CharField(max_length=9, default="#ffffff", validators=[hex_color_validator])

    class Meta:
        unique_together = ("template", "color")

    def __str__(self):
        return f"{self.template} with {self.color}"

    def generate_colors(self):
        self.light_color = colors.generate_light_color(self.color)
        self.save()
