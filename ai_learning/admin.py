from django.contrib import admin

from .models import PromptTemplates, Video, UserConsumedVideos


admin.site.register(PromptTemplates)
admin.site.register(Video)
admin.site.register(UserConsumedVideos)
