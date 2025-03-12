from django.utils import timezone
from celery import shared_task
from uuid import uuid4

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

@shared_task
def process_flashback(flashback_id: int):
    from django.core.files.base import ContentFile
    from event.models import Flashback, FlashbackMediaType
    import cv2
    import os

    instance: Flashback = Flashback.objects.filter(id=flashback_id).first()
    if instance is None or instance.is_processed:
        return

    # dont have to process picture
    if instance.media_type == FlashbackMediaType.PHOTO:
        instance.is_processed = True
        instance.save()
        print("x")
        return

    # make sure the video is in portrait mode
    cap = cv2.VideoCapture(instance.video_media.path)

    cap_red_suc, frame = cap.read()
    if not cap_red_suc or frame is None:
        cap.release()
        return

    frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    if frame_height < frame_width:
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        temp_output_path = instance.video_media.path.replace(".mp4", ".temp.mp4")

        out = cv2.VideoWriter(temp_output_path, fourcc, fps, (frame_height, frame_width))
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rotated_frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
            out.write(rotated_frame)

        cap.release()
        out.release()

        os.replace(temp_output_path, instance.video_media.path)

    # generate preview image for of video
    cap = cv2.VideoCapture(instance.video_media.path)
    cap_red_suc, frame = cap.read()
    cap.release()
    if not cap_red_suc:
        return

    code_suc, buffer = cv2.imencode(".jpg", frame)
    if not code_suc:
        return

    preview = ContentFile(buffer.tobytes())
    instance.media.save(name=f"{uuid4()}.jpg", content=preview, save=True)
    instance.is_processed = True
    instance.save()
    instance.refresh_from_db()

    print(instance.is_processed)


