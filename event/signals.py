from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from event import models


@receiver(post_save, sender=models.EventInvite)
def check_event_invite_status(sender, instance, **kwargs):
    instance.process()

@receiver(post_save, sender=models.EventPosterTemplateColorPalette)
def color_palette_post_save(sender, instance, **kwargs):
    if kwargs["created"]:
        instance.generate_colors()

@receiver(pre_delete, sender=models.Flashback)
def check_for_preview(sender, instance, **kwargs):
    preview = models.EventPreview.objects.filter(flashback=instance).first()
    if preview is not None:
        preview.switch_flashback_random()
