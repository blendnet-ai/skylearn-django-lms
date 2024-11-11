import uuid

from common.models import TimeStampedModel
from django.contrib.auth import get_user_model
from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from data_repo.models import QuestionBank


class UserQuestionAttempt(TimeStampedModel):
    """
    This model stores user attempt session
    """
    class AttemptStatus(models.TextChoices):
        NOT_ATTEMPTED = "NA", _("Not Attempted")
        ATTEMPT_COMPLETED = "AC", _("Attempt Completed")
        ATTEMPT_STARTED = "AS", _("Attempt Started")

    user_id = models.IntegerField(editable=False, null=True,
        help_text=_("Unique ID of the user who attempted.")
    )

    daily_streak = models.IntegerField(default=0,
                                       help_text=_("Count of daily continuos streak including this attempt"))
    attempt_status = models.CharField(max_length=2, choices=AttemptStatus.choices, default=AttemptStatus.NOT_ATTEMPTED)

    @property
    def attempted_at(self):
        return self.created_at

    @property
    def attempt_summary(self):
        """
        Return attempt summary
        """
        pass


class UserAttemptedQuestionResponse(TimeStampedModel):
    """
    This model is used to store the responses to the questions by the user.
    """

    transcript_filename = "transcript.txt"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False,
        help_text=_("Unique ID for this particular User  Question Response.")
    )

    user_question_attempt = models.ForeignKey(UserQuestionAttempt, related_name="response",
                                              on_delete=models.SET_NULL,
                                              null=True, blank=True)

    question_text = models.TextField(max_length=1000, null=True, blank=True,
        help_text=_("Text of the attempted question.")
    )

    question_type = models.CharField(max_length=2, choices=QuestionBank.QuestionType.choices,
                                     null=True, blank=True,
                                     help_text=_("Type of the attempted question.")
    )

    audio_filename = models.CharField(max_length=100, default="audio.wav",
                                       help_text=_("Audio file name as submitted"))

    additional_meta = models.JSONField(null=True, blank=True,
        help_text=_("This field is used to store additional metadata related to the User Attempted Question Response.")
    )

    evaluation_id = models.UUIDField(editable=False,
        help_text=_("Unique ID for evaluation of this particular repsonse.")
    )

    evaluation_score = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True,
                                            help_text=_("Cummulative score of evaluation"))

    evaluation_data = models.JSONField(null=True, blank=True,
        help_text=_("This field is used to store additional metadata related to the user response evaluation.")
    )

    class Meta:
        verbose_name = _("User Attempted Question Response")
        verbose_name_plural = _("User Attempted Question Responses")

    @property
    def audio_path(self):
        path = f"{self.user_question_attempt.user_id}/practice_question_data/{self.id}/speech_data/{self.audio_filename}"
        return path

    @property
    def converted_audio_path(self):
        path = f"{self.user_question_attempt.user_id}/practice_question_data/{self.id}/speech_data/converted_audio.wav"
        return path

    @cached_property
    def transcript_path(self):
        path = f"{self.user_question_attempt.user_id}/practice_question_data/{self.id}/transcription_data/{self.transcript_filename}"
        return path
