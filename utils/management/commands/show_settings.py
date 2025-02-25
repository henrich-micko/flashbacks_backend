from django.core.management.base import BaseCommand
from django.conf import settings

class Command(BaseCommand):
    help = 'Display Django settings'

    def handle(self, *args, **kwargs):
        for setting in dir(settings):
            if setting.startswith("__"):
                continue
            print(setting, ":", getattr(settings, setting))