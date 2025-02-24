from django.contrib import admin

from friendship import models


admin.site.register(models.Friendship)
admin.site.register(models.FriendRequest)