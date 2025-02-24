from django.contrib import admin
from event import models


admin.site.register(models.Event)
admin.site.register(models.EventMember)
admin.site.register(models.Flashback)
admin.site.register(models.EventViewer)
admin.site.register(models.EventPreview)
admin.site.register(models.FlashbackViewer)
admin.site.register(models.EventInviteCode)
admin.site.register(models.EventInvite)
admin.site.register(models.EventPosterTemplate)
admin.site.register(models.EventPosterTemplateColorPalette)
