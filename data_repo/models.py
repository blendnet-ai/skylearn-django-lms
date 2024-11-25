import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils.functional import cached_property
from django.template.defaultfilters import truncatechars

from common.models import TimeStampedModel


class QuestionBank(TimeStampedModel):
    """
    Model to store questions for user to practice
    """
    class QuestionType(models.TextChoices):
        IELTS = "IL", _("IELTS")
        INTERVIEW_PREP = "IP", _("Interview Prep")
        USER_CUSTOM_QUESTION = "CQ", _("Custom question entered by the user")
        
    id = models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)
    question = models.TextField(max_length=1000, help_text=_("Practice question"), 
                                null=True, blank=True)
    hints = models.TextField(max_length=1000, help_text=_("Practice question hints"), 
                                null=True, blank=True)
    type = models.CharField(max_length=2, choices=QuestionType.choices, default=QuestionType.IELTS,
                            help_text=_("Practice question type"))
    response_timelimit = models.SmallIntegerField(default=60, null=True, blank=True,
                                                  help_text=_("Practice question attempt response time limit in secs"))
    is_active = models.BooleanField(default=True, help_text=_("Is practice question active"))

    class Meta:
        verbose_name = _("Question Bank")
        verbose_name_plural = _("Bank Questions")

    @property
    def question_preview(self):
        return truncatechars(self.question, 50)
    
class ConfigMap(TimeStampedModel):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,
        help_text=_("Unique ID for this config map.")
    )
    
    tag = models.CharField(max_length=30, help_text=_("The tag to identify the config."))
    
    config = models.JSONField(help_text=_("Config corresponding to the tag."))
    
    is_active = models.BooleanField(default=False, help_text=_("Is the config active"))
    
    class Meta:
        verbose_name = _("Config Map")
        verbose_name_plural = _("Config Maps")
        constraints = [
            models.UniqueConstraint(
                fields=['tag'], condition=models.Q(is_active=True),
                name='one_active_config_per_tag'
            )
        ]

class InstituteData(models.Model):
    
    id = models.AutoField(primary_key=True)
    institute_name = models.CharField(max_length=255)
    