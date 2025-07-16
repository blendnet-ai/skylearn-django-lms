from django.contrib import admin

from .models import Meeting, MeetingSeries
from .models import ReferenceMaterial

admin.site.register(Meeting)
admin.site.register(MeetingSeries)
admin.site.register(ReferenceMaterial)
