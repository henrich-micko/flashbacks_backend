from django.apps import AppConfig


class FriendshipConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'friendship'

    def ready(self) -> None:
        from friendship import signals
        return super().ready()