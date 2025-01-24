from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin
from modeltranslation.forms import TranslationModelForm

from .models import (
    Quiz,
    Progress,
    Question,
    MCQuestion,
    Choice,
    EssayQuestion,
    Sitting,
)


admin.site.register(Quiz)
admin.site.register(MCQuestion)
admin.site.register(Progress)
admin.site.register(EssayQuestion)
admin.site.register(Sitting)
