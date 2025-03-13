from django.utils import timezone
from celery import shared_task

from event.models import Event, Flashback


""" Global running tasks """

@shared_task
def check_event_status():
    current_time = timezone.now()
    closed_events = Event.objects.filter(end_at__lt=current_time, post_close_actions=False)

    for event in closed_events:
        event.on_close()
        event.post_close_actions = True
        event.save()


@shared_task
def check_flashbacks_nsfw():
    for flashback in Flashback.objects.filter(is_nsfw=None, is_processed=True):
        check_nsfw_flashbacks.s(flashback.id)


@shared_task
def process_flashbacks():
    for flashback in Flashback.objects.filter(is_processed=False):
        process_flashback.delay(flashback.id)


""" Flashbacks instance spec tasks """

@shared_task
def check_nsfw_flashbacks(flashback_id: int):
    Flashback.objects.get(id=flashback_id).check_nsfw()


@shared_task
def process_flashback(flashback_id: int):
    Flashback.objects.get(id=flashback_id).process_media()



