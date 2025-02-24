from django.utils import timezone
from celery import shared_task

from event.models import Event


@shared_task
def check_nsfw_flashbacks(flashback_id: int):
    from event.models import Flashback
    Flashback.objects.get(id=flashback_id).check_nsfw()

@shared_task
def check_event_status():
    current_time = timezone.now()
    closed_events = Event.objects.filter(end_at__lt=current_time, post_close_actions=False)

    for event in closed_events:
        event.on_close()
        event.post_close_actions = True
        event.save()
