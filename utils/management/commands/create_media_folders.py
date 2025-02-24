import os
from django.conf import settings
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = "Creates media root and subdirectories"

    def handle(self, *args, **kwargs):
        media_root = getattr(settings, 'MEDIA_ROOT', None)

        if not media_root:
            self.stderr.write(self.style.ERROR("MEDIA_ROOT is not set in settings.py"))
            return

        folders = ['event_qrcode', 'flashback', 'poster', 'profile']

        for folder in folders:
            path = os.path.join(media_root, folder)
            os.makedirs(path, exist_ok=True)

        self.stdout.write(self.style.SUCCESS("Media directories created successfully!"))
