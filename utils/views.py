from rest_framework.exceptions import ParseError, ValidationError
from typing import Any


def prevent_not_null(*args: Any) -> None:
    for item in args:
        if item is None: raise ParseError("Null is not allowed in args.")


def parse_boolean_value(value: str, default: Any = False) -> Any:
    if type(value) != str: return default
    value = value.lower()
    if value in ["true", "1"]: return True
    if value in ["false", "0"]: return False
    return default

def parse_int_value(params: dict, key: str, **kwargs) -> Any:
    value = params.get(key, None)
    if value is None:
        if "default" in kwargs.keys():
            return kwargs["default"]
        raise ValidationError({key: f"{key} must be set."})

    try: return int(value)
    except (ValueError, TypeError):
        raise ValidationError({key: f"{key} cant parse int from f{value}"})


def parse_str_value(params: dict, key: str) -> Any:
    value = params.get(key, None)
    if value is None:
        raise ValidationError({key: f"{key} must be set."})
    return value
