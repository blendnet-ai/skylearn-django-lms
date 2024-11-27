from django.contrib import admin

from practice.models import UserAttemptedQuestionResponse, UserQuestionAttempt
from .models import Question, AssessmentAttempt, UserEvalQuestionAttempt, AssessmentGenerationConfig

admin.site.register(UserQuestionAttempt)
admin.site.register(UserAttemptedQuestionResponse)

admin.site.register(Question)
admin.site.register(UserEvalQuestionAttempt)
admin.site.register(AssessmentAttempt)
admin.site.register(AssessmentGenerationConfig)
