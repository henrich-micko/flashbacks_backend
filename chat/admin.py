from django.contrib import admin
from chat import models


admin.site.register(models.Message)
admin.site.register(models.LikedMessage)