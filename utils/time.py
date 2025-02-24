from django.utils import timezone


def humanize_event_time(date: timezone.datetime) -> str:
    delta = date - timezone.now()

    if delta.total_seconds() < 0:
        return "Already started"
    if delta < timezone.timedelta(minutes=1):
        return "Starting soon"
    elif delta < timezone.timedelta(hours=1):
        minutes = int(delta.total_seconds() // 60)
        return f"Starting in {minutes} minute{'s' if minutes > 1 else ''}"
    elif delta < timezone.timedelta(days=1):
        hours = int(delta.total_seconds() // 3600)
        return f"Starting in {hours} hour{'s' if hours > 1 else ''}"
    elif delta < timezone.timedelta(weeks=1):
        days = delta.days
        return f"Starting in {days} day{'s' if days > 1 else ''}"
    elif delta < timezone.timedelta(days=30):
        weeks = delta.days // 7
        return f"Starting in {weeks} week{'s' if weeks > 1 else ''}"
    elif delta < timezone.timedelta(days=365):
        months = delta.days // 30
        return f"Starting in {months} month{'s' if months > 1 else ''}"
    else:
        years = delta.days // 365
        return f"Starting in {years} year{'s' if years > 1 else ''}"
