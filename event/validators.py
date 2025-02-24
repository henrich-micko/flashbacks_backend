from django.utils import timezone
from django.core.validators import RegexValidator
from rest_framework.serializers import ValidationError
from datetime import datetime


def validate_event_datetimes(start_at: datetime, end_at: datetime) -> None:
    if not timezone.now() < start_at < end_at:
        raise ValidationError({"timing": "Invalid date times"})


hex_color_validator = RegexValidator(
    regex=r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{8})$',  # Matches #RRGGBB or #RRGGBBAA
    message="Enter a valid hex color code (e.g., #FFFFFF or #FFFFFFFF).",
    code='invalid_hex_color'
)