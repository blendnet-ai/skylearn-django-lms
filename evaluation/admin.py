from django.contrib import admin

from .models import Question, AssessmentAttempt, UserEvalQuestionAttempt, AssessmentGenerationConfig


admin.site.register(Question)
admin.site.register(UserEvalQuestionAttempt)
admin.site.register(AssessmentAttempt)
admin.site.register(AssessmentGenerationConfig)
