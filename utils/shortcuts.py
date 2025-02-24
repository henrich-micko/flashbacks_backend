from django.db.models import Model, QuerySet
from typing import Any


def get_or_default(db_model: Model, key_value: int, default: Any = None, key: str = "pk"):
    try: return db_model.objects.get(**{key: key_value})
    except db_model.DoesNotExist: return default


def url_int(par_name: str) -> str:
    return f"(?P <{par_name}>[^ /.]+)"


def get_object_or_exception(queryset: QuerySet, exception: Exception, **kwargs) -> Model:
    instance = queryset.filter(**kwargs).first()
    if instance is None:
        raise exception
    return instance
