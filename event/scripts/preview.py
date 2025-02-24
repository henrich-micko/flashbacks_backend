from event.models import Event

e = Event.objects.first()
e.generate_preview()