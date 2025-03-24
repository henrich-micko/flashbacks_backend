from django.utils import timezone
from celery import shared_task

from event.models import Event, Flashback, FlashbackMediaType, FlashbackVideoCheckNsfwJob
from utils import nsfw_detection


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
        check_nsfw_flashbacks.delay(flashback.id)


@shared_task
def process_flashbacks():
    for flashback in Flashback.objects.filter(is_processed=False):
        process_flashback.delay(flashback.id)


""" Flashbacks instance spec tasks """


@shared_task
def check_nsfw_flashbacks(flashback_id: int):
    flashback = Flashback.objects.get(id=flashback_id)

    if flashback.media_type == FlashbackMediaType.PHOTO:
        if not flashback.media:
            return

        categories, flashback.is_nsfw = nsfw_detection.check_nsfw_photo_aws(flashback.media_key)
        flashback.save()

    if flashback.media_type == FlashbackMediaType.VIDEO:
        if not flashback.video_media:
            return

        flashback_nsfw_job, created = FlashbackVideoCheckNsfwJob.objects.get_or_create(
            flashback=flashback
        )

        if not flashback_nsfw_job.is_valid:
            flashback_nsfw_job.delete()
            return

        if created:
            flashback_nsfw_job.job_id = nsfw_detection.start_video_moderation(flashback.video_media_key)
            flashback_nsfw_job.save()
            return

        categories, is_nsfw = flashback_nsfw_job.load_result()
        if is_nsfw is not None:
            flashback.is_nsfw = is_nsfw
            flashback.save()
            flashback_nsfw_job.delete()


@shared_task
def process_flashback(flashback_id: int):
    Flashback.objects.get(id=flashback_id).process_media()



