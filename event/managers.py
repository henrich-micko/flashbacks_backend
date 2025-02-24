from django.db import models
from event.status import EventStatus


class EventQuerySet(models.QuerySet):
    def filter_by_status(self, status: EventStatus) -> models.QuerySet:
        status = [status]
        if status[0] == EventStatus.OPENED.value: status.append(EventStatus.ACTIVE.value)
        elif status[0] == EventStatus.ACTIVE.value: status.append(EventStatus.OPENED.value)
        print(status)

        return self.filter(id__in=[
            instance.id for instance in self.all() if instance.status.value in status
        ])


class FlashbackQuerySet(models.QuerySet):
    def first_unseen(self):
        return self.filter(seen=False).order_by("created_at").first()