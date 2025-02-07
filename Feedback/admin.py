from django.contrib import admin

from .models import FeedbackForm, FeedbackResponse

admin.site.register(FeedbackForm)
admin.site.register(FeedbackResponse)
