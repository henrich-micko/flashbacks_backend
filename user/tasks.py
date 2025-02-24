from celery import shared_task


@shared_task()
def check_nsfw_user_profile_picture(user_id: int):
    from user.models import User
    User.objects.get(id=user_id).check_nsfw_profile_picture()
